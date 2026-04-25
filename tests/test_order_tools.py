import unittest

from tools import _menu_validation_message


class OrderToolMenuValidationTest(unittest.TestCase):
    def test_rejects_unknown_menu_item(self) -> None:
        result = _menu_validation_message("김치찌개 하나")

        self.assertIsNotNone(result)
        self.assertIn("현재 메뉴에서 확인하지 못했습니다", result)

    def test_rejects_mixed_unknown_menu_item(self) -> None:
        result = _menu_validation_message("Margherita Pizza 하나, 김치찌개 하나")

        self.assertIsNotNone(result)
        self.assertIn("일부 요청 메뉴를 현재 메뉴에서 확인하지 못했습니다", result)
        self.assertIn("Margherita Pizza", result)
        self.assertIn("김치찌개", result)

    def test_accepts_menu_item(self) -> None:
        result = _menu_validation_message("Margherita Pizza 하나")

        self.assertIsNone(result)
