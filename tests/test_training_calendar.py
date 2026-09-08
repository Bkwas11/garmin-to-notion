import unittest
from datetime import date

from src.helpers._training_calendar import (
    completion_status,
    parse_scheduled_workouts,
    summarize_activities,
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

    def test_requires_both_mileage_and_planned_workout(self):
        self.assertEqual(
            completion_status(5, 5.01, {"strength"}, {"running", "strength"}),
            (True, True, True),
        )
        self.assertEqual(
            completion_status(5, 5.01, {"strength"}, {"running"}),
            (True, False, False),
        )


if __name__ == "__main__":
    unittest.main()
