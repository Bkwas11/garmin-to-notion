import unittest
from datetime import date

from src.helpers._training_calendar import (
    completion_status,
    parse_scheduled_workouts,
    sleep_status,
    summarize_activities,
    weekly_summary,
)


class TrainingCalendarTests(unittest.TestCase):
    def test_parses_only_scheduled_workouts(self):
        payload = {
            "calendarItems": [
                {
                    "itemType": "workout",
                    "date": "2026-09-08",
                    "title": "Upper Body Strength",
                    "workoutId": 123,
                    "sportType": {"sportTypeKey": "strength_training"},
                },
                {
                    "itemType": "activity",
                    "date": "2026-09-08",
                    "title": "Completed Run",
                },
            ]
        }
        workouts = parse_scheduled_workouts(payload)
        self.assertEqual(len(workouts), 1)
        self.assertEqual(workouts[0]["name"], "Upper Body Strength")
        self.assertEqual(workouts[0]["sport_key"], "strength_training")

    def test_sums_only_running_distance_as_miles(self):
        activities = [
            {
                "startTimeLocal": "2026-09-08 07:00:00",
                "activityName": "Morning Run",
                "activityType": {"typeKey": "running"},
                "distance": 8046.72,
            },
            {
                "startTimeLocal": "2026-09-08 17:00:00",
                "activityName": "Lift",
                "activityType": {"typeKey": "strength_training"},
                "distance": 0,
            },
        ]
        summary = summarize_activities(activities)[date(2026, 9, 8)]
        self.assertEqual(round(summary["run_miles"], 2), 5.0)
        self.assertEqual(summary["categories"], {"running", "strength"})
        self.assertEqual(summary["category_counts"]["strength"], 1)

    def test_requires_both_mileage_and_planned_workout(self):
        self.assertEqual(
            completion_status(5, 5.01, {"strength"}, {"running", "strength"}),
            (True, True, True),
        )
        self.assertEqual(
            completion_status(5, 5.01, {"strength"}, {"running"}),
            (True, False, False),
        )

    def test_sleep_status_thresholds(self):
        self.assertEqual(sleep_status(8), "🟢 8+ hours")
        self.assertEqual(sleep_status(7), "🟡 7+ hours")
        self.assertEqual(sleep_status(6.99), "Under 7 hours")
        self.assertIsNone(sleep_status(None))

    def test_formats_weekly_summary(self):
        self.assertEqual(
            weekly_summary(18.2, 20, 4, 5, 2, 3, 7.6, 5, 7),
            "🏃 18.2/20.0 mi · 🎯 4/5 run goals · 🏋️ 2/3 strength · "
            "😴 7.6h avg, 5/7 ≥7h",
        )


if __name__ == "__main__":
    unittest.main()
