import unittest

from src.helpers._strength_log import is_strength_activity, normalize_exercise_sets


class StrengthLogTests(unittest.TestCase):
    def test_identifies_strength_activities(self):
        self.assertTrue(
            is_strength_activity(
                {"activityType": {"typeKey": "strength_training"}}
            )
        )
        self.assertFalse(is_strength_activity({"activityType": {"typeKey": "running"}}))

    def test_normalizes_active_sets_and_skips_rest(self):
        activity = {
            "activityId": 123,
            "activityName": "Upper Body A",
            "startTimeLocal": "2026-09-08 17:00:00",
        }
        payload = {
            "exerciseSets": [
                {
                    "setType": "ACTIVE",
                    "repetitionCount": 8,
                    "weight": 45359.237,
                    "duration": 32.4,
                    "exercises": [
                        {
                            "category": "BENCH_PRESS",
                            "name": "BARBELL_BENCH_PRESS",
                            "probability": 99,
                        }
                    ],
                },
                {"setType": "REST", "duration": 90},
                {
                    "setType": "ACTIVE",
                    "repetitionCount": 6,
                    "weight": 45359.237,
                    "duration": 28,
                    "exercises": [
                        {"category": "BENCH_PRESS", "probability": 99}
                    ],
                },
            ]
        }

        rows = normalize_exercise_sets(activity, payload)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["exercise"], "Barbell Bench Press")
        self.assertEqual(rows[0]["weight_lb"], 100.0)
        self.assertEqual(rows[0]["volume_lb"], 800.0)
        self.assertEqual(rows[0]["set_key"], "123:1")
        self.assertEqual(rows[1]["set_key"], "123:3")


if __name__ == "__main__":
    unittest.main()
