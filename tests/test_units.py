import unittest

from src.helpers._units import (
    format_duration,
    format_pace_per_mile,
    format_race_pace_per_mile,
    meters_to_miles,
)


class UnitFormattingTests(unittest.TestCase):
    def test_formats_eight_minute_mile(self):
        self.assertEqual(format_pace_per_mile(1609.344 / 480), "8:00 min/mi")

    def test_zero_speed_has_no_pace(self):
        self.assertEqual(format_pace_per_mile(0), "")

    def test_duration_rounds_to_nearest_second(self):
        self.assertEqual(format_duration(386.24, "/mi"), "6:26 /mi")

    def test_converts_five_kilometre_record_to_mile_pace(self):
        self.assertEqual(format_race_pace_per_mile(1200, 5), "6:26 /mi")

    def test_converts_metres_to_miles(self):
        self.assertEqual(meters_to_miles(1609.344), 1.0)
        self.assertEqual(meters_to_miles(None), 0.0)


if __name__ == "__main__":
    unittest.main()
