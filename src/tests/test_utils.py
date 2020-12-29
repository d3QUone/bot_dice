from unittest import TestCase

from src.utils.misc import prepare_str


class MiscTestCase(TestCase):

    def test_prepare_str(self):
        res = prepare_str([1, 2])
        self.assertEqual(res, '1\n2')
