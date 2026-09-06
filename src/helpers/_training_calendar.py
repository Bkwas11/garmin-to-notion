from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

from ._units import METERS_PER_MILE


def month_bounds(day: date) -> tuple[date, date]:
    return day.replace(day=1), day.replace(day=monthrange(day.year, day.month)[1])


def dates_in_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def activity_category(type_key: str | None, name: str = "") -> str:
    value = f"{type_key or ''} {name}".lower().replace("_", " ")
    if "run" in value:
        return "running"
    if "strength" in value or "weight" in value:
        return "strength"
    if "cycle" in value or "cycling" in value or "bike" in value:
        return "cycling"
    if "walk" in value:
        return "walking"
    if "swim" in value:
        return "swimming"
    if "row" in value:
        return "rowing"
    if "yoga" in value:
        return "yoga"
    return (type_key or "other").lower().replace("_", " ")


def _sport_type_key(item: dict[str, Any]) -> str | None:
    for container in (item, item.get("workout") or {}):
        sport_type = container.get("sportType") or container.get("activityType")
        if isinstance(sport_type, dict):
            value = sport_type.get("sportTypeKey") or sport_type.get("typeKey")
            if value:
                return str(value)
        if isinstance(sport_type, str):
            return sport_type
    return None


def parse_scheduled_workouts(payload: Any) -> list[dict[str, str]]:
    """Normalize Garmin calendar workout items while ignoring events/activities."""
    if isinstance(payload, dict):
        items = (
            payload.get("calendarItems")
            or payload.get("scheduledWorkouts")
            or payload.get("workoutScheduleList")
            or []
        )
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    workouts: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        nested = item.get("workout") if isinstance(item.get("workout"), dict) else {}
        item_type = str(item.get("itemType") or "").lower()
        workout_id = item.get("workoutId") or nested.get("workoutId")
        is_workout = bool(workout_id) or "workout" in item_type
        if not is_workout:
            continue

        workout_date = item.get("date") or item.get("scheduledDate")
        if not workout_date:
            continue
        name = (
            item.get("title")
            or item.get("workoutName")
            or nested.get("workoutName")
            or "Garmin Workout"
        )
        sport_key = _sport_type_key(item)
        workouts.append(
            {
                "date": str(workout_date)[:10],
                "name": str(name),
                "workout_id": str(workout_id or ""),
                "sport_key": str(sport_key or ""),
            }
        )
    return workouts


def summarize_activities(
    activities: list[dict[str, Any]],
) -> dict[date, dict[str, Any]]:
    summaries: dict[date, dict[str, Any]] = defaultdict(
        lambda: {"run_miles": 0.0, "categories": set(), "names": []}
    )
    for activity in activities:
        raw_date = activity.get("startTimeLocal") or activity.get("startTimeGMT")
        if not raw_date:
            continue
        try:
            activity_date = date.fromisoformat(str(raw_date)[:10])
        except ValueError:
            continue
        name = str(activity.get("activityName") or "Activity")
        type_key = str((activity.get("activityType") or {}).get("typeKey") or "")
        category = activity_category(type_key, name)
        summary = summaries[activity_date]
        summary["categories"].add(category)
        summary["names"].append(name)
        if category == "running":
            summary["run_miles"] += (
                float(activity.get("distance") or 0) / METERS_PER_MILE
            )
    return dict(summaries)


def completion_status(
    planned_miles: float,
    actual_miles: float,
    planned_categories: set[str],
    actual_categories: set[str],
) -> tuple[bool, bool, bool]:
    has_run_goal = planned_miles > 0
    run_goal_met = has_run_goal and actual_miles + 0.005 >= planned_miles
    workout_complete = bool(planned_categories) and planned_categories.issubset(
        actual_categories
    )
    has_plan = has_run_goal or bool(planned_categories)
    complete = (
        has_plan
        and (not has_run_goal or run_goal_met)
        and (not planned_categories or workout_complete)
    )
    return run_goal_met, workout_complete, complete
