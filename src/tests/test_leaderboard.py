from datetime import timedelta
from unittest import TestCase

from freezegun import freeze_time

from src.leaderboard import LeaderBoard, BoardUserAlreadyExists


class LeaderBoardTestCase(TestCase):
    maxDiff = None

    @freeze_time('2020-12-19T12:00:00.0000')
    def test_first_add_users(self):
        board = LeaderBoard()
        pos = board.add_result(chat_id=1, full_name='F1', result=1)
        self.assertEqual(pos, 1)

        # Нельзя добавлять того же юзера
        with self.assertRaises(BoardUserAlreadyExists):
            board.add_result(chat_id=1, full_name='F1', result=1)

        # Результат обновился
        pos = board.add_result(chat_id=2, full_name='F2', result=2)
        self.assertEqual(pos, 1)

        # Первый юзер сдвинулся
        pos = board.user_stats(chat_id=1)
        self.assertEqual(pos, 2)

        # Начать новый раунд
        board.new_round()

        stats = board.total_stats()
        self.assertEqual(len(stats), 2)

        self.assertEqual(stats[0][0], 1)
        self.assertDictEqual(stats[0][1], {
            'chat_id': 2,
            'full_name': 'F2',
            'result': 2,
            'created_at': 1608379200.0,
        })
        self.assertEqual(stats[1][0], 2)
        self.assertDictEqual(stats[1][1], {
            'chat_id': 1,
            'full_name': 'F1',
            'result': 1,
            'created_at': 1608379200.0,
        })

        # Поставить новый рекорд
        pos = board.add_result(chat_id=1, full_name='FUU', result=10)
        self.assertEqual(pos, 1)

        board.new_round()

        stats = board.total_stats()
        self.assertEqual(len(stats), 2)

        self.assertEqual(stats[0][0], 1)
        self.assertDictEqual(stats[0][1], {
            'chat_id': 1,
            'full_name': 'FUU',
            'result': 10,
            'created_at': 1608379200.0,
        })
        self.assertEqual(stats[1][0], 2)
        self.assertDictEqual(stats[1][1], {
            'chat_id': 2,
            'full_name': 'F2',
            'result': 2,
            'created_at': 1608379200.0,
        })

    @freeze_time('2020-12-19T12:00:00.0000')
    def test_time_left(self):
        board = LeaderBoard()
        self.assertEqual(board.time_left, 120.0)

    def test_result_expire(self):
        board = LeaderBoard(
            round_duration=timedelta(seconds=10),
            expire_delta=timedelta(seconds=20),
        )
        board.add_result(chat_id=1, full_name='FUU', result=10)

        # Обновить результаты
        for _ in range(2):
            board.new_round()
            stats = board.total_stats()
            self.assertEqual(len(stats), 1)

        # Снова обновить результаты, в этот раз пришло время очищать результаты
        board.new_round()
        stats = board.total_stats()
        self.assertEqual(len(stats), 0)
