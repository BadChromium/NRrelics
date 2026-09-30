import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from core.repo_cleaner import RepoCleaner
from core.relic_detector import RELIC_STATE_LIGHT


class SaleNavigationTests(unittest.TestCase):
    def setUp(self):
        self.cleaner = object.__new__(RepoCleaner)
        self.cleaner.is_running = True
        self.cleaner.stop_reason = None
        self.cleaner.pending_sell_count = 0
        self.cleaner.stats = {"sold": 0}
        self.previous = (1035, 207, 99, 98)
        self.next = (1145, 207, 99, 98)
        self.cleaner.repository_filter = SimpleNamespace(
            scale_x=1, scale_y=1, _capture_game_window=Mock(return_value=object()))
        self.cleaner.relic_detector = SimpleNamespace(detect_cursor=Mock())
        self.logs = []
        self.log = lambda message, level: self.logs.append((message, level))

    def test_stationary_after_f_moves_right_once_and_verifies(self):
        self.cleaner.relic_detector.detect_cursor.side_effect = [
            (self.previous, 99), (self.previous, 99), (self.next, 99)]
        with patch("core.repo_cleaner.pydirectinput.press") as press, \
             patch("core.repo_cleaner.time.sleep"):
            need_right = self.cleaner._execute_action(RELIC_STATE_LIGHT, False, "sell", self.log)
            advanced = self.cleaner._advance_after_sale_selection(self.previous, self.log)
        self.assertFalse(need_right)
        self.assertTrue(advanced)
        self.assertEqual(press.call_args_list, [unittest.mock.call("f"), unittest.mock.call("right")])
        self.assertEqual(self.cleaner.pending_sell_count, 1)

    def test_auto_advanced_after_f_does_not_skip_another_item(self):
        self.cleaner.relic_detector.detect_cursor.return_value = (self.next, 99)
        with patch("core.repo_cleaner.pydirectinput.press") as press, \
             patch("core.repo_cleaner.time.sleep"):
            self.assertTrue(self.cleaner._advance_after_sale_selection(self.previous, self.log))
        press.assert_not_called()

    def test_unknown_cursor_stops_without_another_key(self):
        self.cleaner.relic_detector.detect_cursor.return_value = (None, None)
        with patch("core.repo_cleaner.pydirectinput.press") as press, \
             patch("core.repo_cleaner.time.sleep"):
            self.assertFalse(self.cleaner._advance_after_sale_selection(self.previous, self.log))
        press.assert_not_called()
        self.assertEqual(self.cleaner.stop_reason, "error")


if __name__ == "__main__":
    unittest.main()
