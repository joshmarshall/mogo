import unittest

from mogo.helpers import check_none


class TestHelpers(unittest.TestCase):

    def test_check_none_raises_value_error_if_null(self) -> None:
        with self.assertRaises(ValueError):
            check_none(None)

    def test_check_none_returns_value_if_not_null(self) -> None:
        self.assertEqual(5, check_none(5))
        self.assertEqual(True, check_none(True))

    def test_check_none_returns_pointers_if_not_null(self) -> None:
        def cb() -> int:
            return 5

        self.assertEqual(cb, check_none(cb))
