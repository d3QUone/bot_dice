import time
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import chain
from typing import List, Tuple, Optional

from src.utils.storage import Storage


class BoardException(Exception):
    pass


class BoardUserAlreadyExists(BoardException):
    """Нельзя добавлять юзера повторно когда он уже принял участие в раунде."""


@dataclass
class LeaderItem:
    """LeaderItem представляет одного пользователя в таблице рекордов."""
    chat_id: int
    full_name: str
    score: int
    created_at: float

    def __str__(self) -> str:
        created_at = datetime.fromtimestamp(self.created_at).strftime('%H:%M %d.%m.%Y')
        return f'[[{self.full_name}]] - *{self.score}* - {created_at}'


POS_NOT_FOUND = -1


def find_user_pos(array: List[LeaderItem], chat_id: int) -> Tuple[int, Optional[LeaderItem]]:
    for pos, item in enumerate(array):
        if item.chat_id == chat_id:
            return pos + 1, item
    return POS_NOT_FOUND, None


def sort_board(array: List[LeaderItem]) -> List[LeaderItem]:
    return sorted(array, key=lambda i: (i.score, i.created_at), reverse=True)


class LeaderBoard:
    """LeaderBoard представляет основную и единую логику таблицы рекордов."""

    def __init__(self, round_duration: timedelta = None, expire_delta: timedelta = None, dry_run: bool = False):
        self.last_game_storage = Storage(filename='last_game', klass=LeaderItem, dry_run=dry_run)
        self.last_game: List[LeaderItem] = self.last_game_storage.load()

        self.last_day_storage = Storage(filename='last_day', klass=LeaderItem, dry_run=dry_run)
        self.last_day: List[LeaderItem] = self.last_day_storage.load()

        # Какое кол-во рекордов отображать в статистике
        self.visible_leader_board = 10
        # Длительность раунда
        self.round_duration = round_duration or timedelta(minutes=2)
        # Срок жизни результатов
        self.expire_delta = expire_delta or timedelta(hours=24)
        # Сколько раундов прошло
        self.round_counter = 0
        # Время последнего обновления
        self.last_update = time.time()

    def run_update(self):
        """Запустить фоновое обновление счётчиков."""

        def inner():
            while True:
                time.sleep(self.round_duration.total_seconds())

                self.new_round()
                self.dump_data()
                self.last_update = time.time()

        t = threading.Thread(target=inner, daemon=True)
        t.start()

    def dump_data(self):
        """Сохранить промежуточные результаты."""
        self.last_game_storage.save(objs=self.last_game)
        self.last_day_storage.save(objs=self.last_day)

    @property
    def time_left(self) -> float:
        """Сколько времени осталось до начала нового раунда."""
        now = time.time()
        return self.last_update + self.round_duration.total_seconds() - now

    def user_stats(self, chat_id: int) -> int:
        """Текущая позиция пользователя в этом раунде."""
        pos, _ = find_user_pos(array=self.last_game, chat_id=chat_id)
        return pos

    def can_add_result(self, chat_id: int) -> bool:
        """Может ли пользователь участвовать в текущем раунде."""
        return self.user_stats(chat_id=chat_id) == POS_NOT_FOUND

    def add_result(self, chat_id: int, full_name: str, score: int) -> int:
        """Добавить результат в общую таблицу, и вернуть место пользователя в текущем раунде."""
        if not self.can_add_result(chat_id=chat_id):
            raise BoardUserAlreadyExists

        item = LeaderItem(
            chat_id=chat_id,
            full_name=full_name,
            score=score,
            created_at=time.time(),
        )
        self.last_game.append(item)

        self.last_game = sort_board(self.last_game)
        return self.user_stats(chat_id=chat_id)

    def new_round(self):
        """ Новый раунд игры. Текущие результаты переносятся в суточный рекорд.
            Учесть что пользователь уже может быть в рекордах, и нужно выбрать
            один максимальный результат от него.
        """
        # Проверить пришло ли время обнулять все результаты.
        count = int(self.expire_delta.total_seconds() / self.round_duration.seconds)
        if self.round_counter % count == 0:
            self.last_day = []

        games_dict = defaultdict(list)
        for i in chain(self.last_day, self.last_game):
            games_dict[i.chat_id].append(i)

        self.last_day = sort_board([max(group, key=lambda i: i.score) for group in games_dict.values()])
        self.last_game = []

        self.round_counter += 1

    def abs_stats(self, array, chat_id: int = None) -> List[Tuple[int, LeaderItem]]:
        """Вернуть текущие рекорды + позицию пользователя."""
        leaders = array[:self.visible_leader_board]
        res = [(inx + 1, item) for inx, item in enumerate(leaders)]

        if chat_id is not None:
            pos, us = find_user_pos(array=array, chat_id=chat_id)
            if pos != POS_NOT_FOUND and pos > self.visible_leader_board:
                res.append((pos, us))

        return res

    def total_stats(self, chat_id: int = None) -> List[Tuple[int, LeaderItem]]:
        return self.abs_stats(array=self.last_day, chat_id=chat_id)

    def current_stats(self, chat_id: int = None) -> List[Tuple[int, LeaderItem]]:
        return self.abs_stats(array=self.last_game, chat_id=chat_id)
