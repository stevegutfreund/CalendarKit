import unittest
from datetime import date, datetime

from calendarkit import hebrew
from calendarkit.hebrew import HebrewDate


class ShkiaRule(unittest.TestCase):
    def test_after_shkia_moves_to_next_hebrew_day(self):
        d = date(2026, 11, 16)
        self.assertEqual(hebrew.to_hebrew(d, after_shkia=True), hebrew.to_hebrew(date(2026, 11, 17)))
        self.assertEqual(hebrew.to_hebrew(d, False), HebrewDate.from_pydate(d))

    def test_accepts_datetime(self):
        self.assertEqual(hebrew.to_hebrew(datetime(2026, 11, 16, 23)), hebrew.to_hebrew(date(2026, 11, 16)))

    def test_days_between(self):
        a, b = date(2026, 1, 1), date(2026, 1, 29)
        self.assertEqual(hebrew.hebrew_days_between(b, False, a, False), 28)
        self.assertEqual(hebrew.hebrew_days_between(b, True, a, False), 29)
        self.assertEqual(hebrew.hebrew_days_between(b, False, a, True), 27)
        # after shkia on D and before shkia on D+1 are the same Hebrew day
        self.assertEqual(hebrew.hebrew_days_between(date(2026, 1, 2), False, a, True), 0)


class Anniversaries(unittest.TestCase):
    def test_adar_ii_falls_back_in_regular_year(self):
        born = HebrewDate(5784, 13, 10)            # 5784 is a leap year
        self.assertTrue(hebrew.is_leap_year(5784))
        self.assertFalse(hebrew.is_leap_year(5785))
        self.assertEqual(hebrew.anniversary_in_year(born, 5785), HebrewDate(5785, 12, 10))
        self.assertEqual(hebrew.anniversary_in_year(born, 5787), HebrewDate(5787, 13, 10))

    def test_missing_day_returns_none(self):
        born = None
        for y in range(5780, 5800):                # find a year with 30 Cheshvan
            try:
                born = HebrewDate(y, 8, 30)
                break
            except ValueError:
                continue
        self.assertIsNotNone(born)
        years = [y for y in range(5780, 5800) if hebrew.anniversary_in_year(born, y) is None]
        self.assertTrue(years, "some year should lack 30 Cheshvan")

    def test_next_anniversary(self):
        born = hebrew.to_hebrew(date(2000, 3, 1))
        g, years = hebrew.next_anniversary(born, date(2026, 11, 16))
        self.assertGreaterEqual(g, date(2026, 11, 16))
        self.assertEqual(hebrew.anniversary_in_year(born, born.year + years).to_pydate(), g)


class MonthArithmetic(unittest.TestCase):
    def test_regular(self):
        self.assertEqual(hebrew.same_day_next_month(HebrewDate(5787, 9, 6)), HebrewDate(5787, 10, 6))

    def test_elul_to_tishrei_next_year(self):
        self.assertEqual(hebrew.same_day_next_month(HebrewDate(5786, 6, 5)), HebrewDate(5787, 7, 5))

    def test_adar_transitions(self):
        self.assertEqual(hebrew.same_day_next_month(HebrewDate(5785, 12, 5)), HebrewDate(5785, 1, 5))
        self.assertEqual(hebrew.same_day_next_month(HebrewDate(5784, 12, 5)), HebrewDate(5784, 13, 5))
        self.assertEqual(hebrew.same_day_next_month(HebrewDate(5784, 13, 5)), HebrewDate(5784, 1, 5))

    def test_day_30_into_29_day_month_raises(self):
        with self.assertRaises(ValueError):
            hebrew.same_day_next_month(HebrewDate(5787, 1, 30))   # Nissan 30 -> Iyar has 29


class Formatting(unittest.TestCase):
    def test_english(self):
        self.assertEqual(hebrew.format_hebrew(HebrewDate(5787, 9, 6)), "6 Kislev 5787")
        self.assertEqual(hebrew.format_hebrew(HebrewDate(5784, 13, 1)), "1 Adar II 5784")

    def test_hebrew_letters(self):
        self.assertIn("כסלו", hebrew.format_hebrew(HebrewDate(5787, 9, 6), lang="he"))


if __name__ == "__main__":
    unittest.main()
