from unittest import TestCase

from src.utils.logs import pretty_time_delta
from src.utils.misc import prepare_str


class MiscTestCase(TestCase):

    def test_pretty_time_delta(self):
        r = pretty_time_delta(1)
        self.assertEqual(r, '1 sec')

        r = pretty_time_delta(62)
        self.assertEqual(r, '1 min 2 sec')

        r = pretty_time_delta(3620.1)
        self.assertEqual(r, '1 hours 0 min 20 sec')

        r = pretty_time_delta(93620.1)
        self.assertEqual(r, '1 days 2 hours 0 min 20 sec')

    def test_prepare_str(self):
        res = prepare_str([1, 2])
        self.assertEqual(res, '1\n2')
