import logging
import time
import threading
import os
from collections import defaultdict
from functools import wraps

import asyncio
import sentry_sdk
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Command, IDFilter
from aiogram.dispatcher.filters.filters import AndFilter

from src.constants import (
    ADMIN_IDS,
    COMMAND_HELP,
    COMMAND_ROLL,
    COMMAND_START,
    COMMAND_STATS,
    COMMAND_USER,
    COMMAND_GAME_LEADERS,
    COMMAND_ROUND_LEADERS,
)
from src.leaderboard import LeaderBoard
from src.utils.logs import async_log_exception, pretty_time_delta
from src.utils.misc import prepare_str


logging.basicConfig(
    level=logging.DEBUG,
)
log = logging.getLogger(__name__)


class Manager:

    def __init__(self, token: str, sentry_token: str = None):
        self.bot = Bot(
            token=token,
            timeout=3.0,
        )
        self.dispatcher = Dispatcher(
            bot=self.bot,
        )
        sentry_sdk.init(
            dsn=sentry_token,
            traces_sample_rate=1.0,
        )

        # Game rules
        self.board = LeaderBoard()
        self.update_cycle = 0
        self.round_duration = 2 * 60
        self.last_update = time.time()

        # Runtime stats
        self.counter = 0
        self.unique_chats = set()
        self.started_at = time.time()
        self.func_counter = defaultdict(int)
        self.func_average_resp_time = defaultdict(float)  # milliseconds
        self.func_resp_time = defaultdict(list)  # milliseconds
        self.max_list_size = 1000

    def update_leader_board(self):
        while True:
            time.sleep(self.round_duration)

            self.board.new_round()
            self.update_cycle += 1
            self.last_update = time.time()

    def run(self):
        self.set_up_commands()

        t = threading.Thread(target=self.update_leader_board, daemon=True)
        t.start()

        executor.start_polling(
            dispatcher=self.dispatcher,
            skip_updates=True,
        )

    def increment_counter(self, f):
        """Wrap any important function with this."""

        @wraps(f)
        async def inner(message: types.Message, *args, **kwargs):
            fn = f.__name__
            self.counter += 1
            self.func_counter[fn] += 1

            # Calculate response time
            t0 = time.time()
            res = await f(*args, message, **kwargs)
            dt = (time.time() - t0) * 1000
            self.func_average_resp_time[fn] += dt

            # Store only last X values
            self.func_resp_time[fn] = self.func_resp_time[fn][-(self.max_list_size - 1):]
            self.func_resp_time[fn].append(dt)

            chat_id = message.chat.id
            self.unique_chats.add(chat_id)

            return res

        return inner

    def set_up_commands(self):
        self.dispatcher.register_message_handler(
            self.increment_counter(self.show_welcome),
            Command(commands=[COMMAND_START]),
        )
        self.dispatcher.register_message_handler(
            self.increment_counter(self.show_help),
            Command(commands=[COMMAND_HELP]),
        )

        # Игра
        self.dispatcher.register_message_handler(
            self.increment_counter(self.roll_once),
            Command(commands=[COMMAND_ROLL]),
        )
        self.dispatcher.register_message_handler(
            self.increment_counter(self.roll_stats_round),
            Command(commands=[COMMAND_ROUND_LEADERS]),
        )
        self.dispatcher.register_message_handler(
            self.increment_counter(self.roll_stats_total),
            Command(commands=[COMMAND_GAME_LEADERS]),
        )

        # Прочие вспомогательные команды, admin only
        self.dispatcher.register_message_handler(
            self.show_user_info,
            AndFilter(
                Command(commands=[COMMAND_USER]),
                IDFilter(chat_id=ADMIN_IDS),
            ),
        )
        self.dispatcher.register_message_handler(
            self.show_stats,
            AndFilter(
                Command(commands=[COMMAND_STATS]),
                IDFilter(chat_id=ADMIN_IDS),
            ),
        )

    @async_log_exception
    async def show_welcome(self, message: types.Message):
        text = [
            'Привет! Это бот для бросания шаров. Каждый пользователь может бросить шары только 1 раз за 2 минуты.',
            'Чем больше *произведение* выпавших кегль - тем лучше.',
            '',
            f'Нажми /{COMMAND_HELP} чтобы увидеть список доступных комманд.',
            '',
            f'Или нажми /{COMMAND_ROLL} чтобы сразу бросить шары.',
        ]
        await message.answer(
            text=prepare_str(text=text),
            parse_mode=types.ParseMode.MARKDOWN,
        )

    @async_log_exception
    async def roll_once(self, message: types.Message):
        chat_id = message.chat.id
        now = time.time()

        if not self.board.can_add_result(chat_id=chat_id):
            text = [
                f'*Нельзя бросать слишком часто!*',
                '',
            ]
            # Посчитать точное время
            dt = (self.last_update + self.round_duration) - now
            if dt < 0:
                # Что-то не так с обновлением!
                msg = 'Вы скоро сможете повторить!'
                log.error('something wrong with update thread!')
            else:
                msg = f'Вы сможете повторить в новом раунде через {pretty_time_delta(dt)}!'
            text.append(msg)

            return await message.answer(
                text=prepare_str(text=text),
                parse_mode=types.ParseMode.MARKDOWN,
            )

        # Roll
        rolls = [await message.answer_dice(emoji='🎳') for _ in range(3)]

        val = 1
        for v in rolls:
            val *= v["dice"]["value"]

        # Wait for animation
        await asyncio.sleep(3)

        pos = self.board.add_result(
            chat_id=chat_id,
            full_name=message.chat.full_name,
            result=val,
        )

        text = [
            f'Ваш результат: *{val}*',
            f'Прямо сейчас вы на позиции *{pos}*',
            '',
            f'Посмотреть итоги раунда: /{COMMAND_ROUND_LEADERS}',
            f'Посмотреть лучшие результаты: /{COMMAND_GAME_LEADERS}',
        ]
        await message.answer(
            text=prepare_str(text=text),
            parse_mode=types.ParseMode.MARKDOWN,
        )

    @async_log_exception
    async def roll_stats_round(self, message: types.Message):
        chat_id = message.chat.id
        stats = self.board.current_stats(chat_id=chat_id)
        if not stats:
            return await message.answer(
                text='Пока что ничего нет.',
                parse_mode=types.ParseMode.MARKDOWN,
            )

        text = [
            '*Текущий раунд*',
            '',
        ]

        for pos, item in stats:
            msg_pos = f'*{pos}*' if pos <= 3 else f'{pos}'
            msg = f'{msg_pos}. [[{item["full_name"]}]] {item["result"]}'
            text.append(msg)

        dt = (self.last_update + self.round_duration) - time.time()
        if dt > 0:
            text.extend([
                '',
                f'Новый раунд через: {pretty_time_delta(dt)}',
            ])

        await message.answer(
            text=prepare_str(text=text),
            parse_mode=types.ParseMode.MARKDOWN,
        )

    @async_log_exception
    async def roll_stats_total(self, message: types.Message):
        chat_id = message.chat.id
        stats = self.board.total_stats(chat_id=chat_id)
        if not stats:
            return await message.answer(
                text='Пока что ничего нет.',
                parse_mode=types.ParseMode.MARKDOWN,
            )

        text = [
            '*Лучшие результаты за всё время*',
            '',
        ]

        for pos, item in stats:
            msg_pos = f'*{pos}*' if pos <= 3 else f'{pos}'
            msg = f'{msg_pos}. [[{item["full_name"]}]] {item["result"]}'
            text.append(msg)

        await message.answer(
            text=prepare_str(text=text),
            parse_mode=types.ParseMode.MARKDOWN,
        )

    @async_log_exception
    async def show_user_info(self, message: types.Message):
        text = [
            '*Информация об аккаунте*',
            '',
            f'Имя: `{message.chat.full_name}`',
            f'Идентификатор чата: `{message.chat.id}`',
        ]
        await message.answer(
            text=prepare_str(text=text),
            parse_mode=types.ParseMode.MARKDOWN,
        )

    @async_log_exception
    async def show_help(self, message: types.Message):
        text = [
            '*Боулинг*',
            '',
            f'/{COMMAND_ROLL} -- бросить шары.',
            f'/{COMMAND_ROUND_LEADERS} -- итоги раунда.',
            f'/{COMMAND_GAME_LEADERS} -- лучшие результаты.',
            '',
            '*Помощь*',
            '',
            f'/{COMMAND_START} -- запустить бота.',
            f'/{COMMAND_HELP} -- просмотреть это сообщение ещё раз.',
        ]
        if message.chat.id in ADMIN_IDS:
            text.extend([
                '',
                '*Вспомогательные команды*',
                '',
                f'/{COMMAND_USER} -- посмотреть на себя.',
                f'/{COMMAND_STATS} -- посмотреть статистику бота.',
            ])
        await message.answer(
            text=prepare_str(text=text),
            parse_mode=types.ParseMode.MARKDOWN,
        )

    @async_log_exception
    async def show_stats(self, message: types.Message):
        if not self.func_counter:
            return await message.reply(
                text='Сейчас тут ничего нет.',
            )

        now = time.time()
        lifetime = pretty_time_delta(now - self.started_at)

        text = [
            '*Статистика бота*',
            '',
            f'- Всего запросов с момента старта: *{self.counter}*',
            f'- Всего пользователей с момента старта: *{len(self.unique_chats)}*',
            f'- Время жизни бота: {lifetime}',
            f'- Циклов: {self.update_cycle}, last: {self.last_update}',
            '',
            '*Статистика по функциям*',
            '',
        ]
        total_resp_time = []
        sorted_requests = sorted(self.func_counter.items(), key=lambda i: (i[1], i[0]), reverse=True)
        for (fn, requests) in sorted_requests:
            # AVG resp time
            resp_time = self.func_resp_time[fn]
            total_resp_time.extend(resp_time)
            avg_resp = sum(resp_time) / len(resp_time)

            text.append(f'`{fn}`')
            text.append(f'{requests} requests, {avg_resp:.0f} avg resp time (ms)')
            text.append('')

        # Вставить после ``Всего запросов..``
        total_avg = sum(total_resp_time) / len(total_resp_time)
        text.insert(3, f'- Среднее время ответа: *{total_avg:.0f}* (ms)')

        await message.answer(
            text=prepare_str(text=text),
            parse_mode=types.ParseMode.MARKDOWN,
        )


if __name__ == '__main__':
    TG_TOKEN = os.getenv('TG_TOKEN')
    assert TG_TOKEN, 'TG_TOKEN env variable must be set!'

    SENTRY_TOKEN = os.getenv('SENTRY_TOKEN')

    m = Manager(
        token=TG_TOKEN,
    )
    m.run()
