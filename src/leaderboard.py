import time
from collections import defaultdict
from itertools import chain
from typing import List, TypedDict, Tuple, Optional


class BoardException(Exception):
    pass


class BoardUserAlreadyExists(BoardException):
    """Нельзя добавлять юзера повторно когда он уже принял участие в раунде."""


class LeaderItem(TypedDict):
    """LeaderItem представляет одного пользователя в таблице рекордов."""
    chat_id: int
    full_name: str
    result: int
    created_at: float


POS_NOT_FOUND = -1


def find_user_pos(array: List[LeaderItem], chat_id: int) -> Tuple[int, Optional[LeaderItem]]:
    for pos, item in enumerate(array):
        if item['chat_id'] == chat_id:
            return pos + 1, item
    return POS_NOT_FOUND, None


def sort_board(array: List[LeaderItem]) -> List[LeaderItem]:
    return sorted(array, key=lambda i: (i['result'], i['created_at']), reverse=True)


class LeaderBoard:
    """LeaderBoard представляет основную и единую логику таблицы рекордов."""

    def __init__(self):
        self.last_game: List[LeaderItem] = []
        self.last_day: List[LeaderItem] = []

        self.visible_leader_board = 10

    def add_result(self, chat_id: int, full_name: str, result: int) -> int:
        """Добавить результат в общую таблицу, и вернуть место пользователя в текущем раунде."""
        old_pos, _ = find_user_pos(array=self.last_game, chat_id=chat_id)
        if old_pos != POS_NOT_FOUND:
            raise BoardUserAlreadyExists

        item = LeaderItem(
            chat_id=chat_id,
            full_name=full_name,
            result=result,
            created_at=time.time(),
        )
        self.last_game.append(item)

        self.last_game = sort_board(self.last_game)
        pos, _ = find_user_pos(array=self.last_game, chat_id=chat_id)
        return pos

    def can_add_result(self, chat_id: int) -> bool:
        """Может ли пользователь участвовать в текущем раунде."""
        pos, _ = find_user_pos(array=self.last_game, chat_id=chat_id)
        return pos == POS_NOT_FOUND

    def user_stats(self, chat_id: int) -> int:
        """Текущая позиция пользователя в этом раунде."""
        pos, _ = find_user_pos(array=self.last_game, chat_id=chat_id)
        return pos

    def new_round(self):
        """ Новый раунд игры. Текущие результаты переносятся в суточный рекорд.
            Учесть что пользователь уже может быть в рекордах, и нужно выбрать
            один максимальный результат от него.
        """
        games_dict = defaultdict(list)
        for i in chain(self.last_day, self.last_game):
            games_dict[i['chat_id']].append(i)

        self.last_day = sort_board([max(group, key=lambda i: i['result']) for group in games_dict.values()])
        self.last_game = []

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
