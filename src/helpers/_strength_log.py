from __future__ import annotations

from collections import defaultdict
from typing import Any

GRAMS_PER_POUND = 453.59237


def is_strength_activity(activity: dict[str, Any]) -> bool:
    activity_type = str(
        (activity.get("activityType") or {}).get("typeKey") or ""
    ).lower()
    activity_name = str(activity.get("activityName") or "").lower()
    return "strength" in activity_type or "strength" in activity_name


def _display_name(value: str | None) -> str:
    if not value:
        return "Unknown Exercise"
    return value.replace("_", " ").strip().title()


def _exercise_name(exercise_set: dict[str, Any]) -> str:
    exercises = exercise_set.get("exercises") or []
    if not exercises:
        return "Unknown Exercise"

    ranked = sorted(
        (exercise for exercise in exercises if isinstance(exercise, dict)),
        key=lambda exercise: float(exercise.get("probability") or 0),
        reverse=True,
    )
    for exercise in ranked:
        name = exercise.get("name")
        category = exercise.get("category")
        candidate = name or category
        if candidate and str(candidate).upper() != "UNKNOWN":
            return _display_name(str(candidate))
    return "Unknown Exercise"


def _set_type(value: str | None) -> str:
    mapping = {
        "ACTIVE": "Active",
        "WARMUP": "Warmup",
        "DROP_SET": "Drop Set",
        "FAILURE": "Failure",
    }
    return mapping.get(str(value or "").upper(), "Other")


def normalize_exercise_sets(
    activity: dict[str, Any], payload: dict[str, Any]
) -> list[dict[str, Any]]:
    """Normalize Garmin's strength-set response into Notion-ready rows."""
    activity_id = str(activity.get("activityId") or payload.get("activityId") or "")
    activity_date = str(
        activity.get("startTimeLocal") or activity.get("startTimeGMT") or ""
    )[:10]
    workout_name = str(activity.get("activityName") or "Strength Training")
    exercise_counts: defaultdict[str, int] = defaultdict(int)
    rows: list[dict[str, Any]] = []

    for source_index, exercise_set in enumerate(payload.get("exerciseSets") or [], 1):
        if not isinstance(exercise_set, dict):
            continue
        raw_type = str(exercise_set.get("setType") or "").upper()
        if raw_type == "REST":
            continue

        exercise = _exercise_name(exercise_set)
        exercise_counts[exercise] += 1
        set_number = exercise_counts[exercise]
        reps = int(exercise_set.get("repetitionCount") or 0)
        weight_lb = round(float(exercise_set.get("weight") or 0) / GRAMS_PER_POUND, 2)
        rows.append(
            {
                "set_key": f"{activity_id}:{source_index}",
                "date": activity_date,
                "workout": workout_name,
                "exercise": exercise,
                "set_number": set_number,
                "set_type": _set_type(raw_type),
                "reps": reps,
                "weight_lb": weight_lb,
                "volume_lb": round(reps * weight_lb, 2),
                "duration_sec": round(float(exercise_set.get("duration") or 0), 2),
                "activity_id": activity_id,
            }
        )
    return rows
