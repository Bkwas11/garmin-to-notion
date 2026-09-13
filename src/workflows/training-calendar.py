from __future__ import annotations

import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient

from src.helpers import get_garmin_client, get_notion_client
from src.helpers._training_calendar import (
    activity_category,
    format_planned_workouts,
    dates_in_range,
    month_bounds,
    parse_scheduled_workouts,
    sleep_status,
    summarize_activities,
    weekly_summary,
)

CALENDAR_PROPERTIES = {
    "Day": "title",
    "Date": "date",
    "Miles Planned": "number",
    "Miles Run": "number",
    "Workout Planned": "rich_text",
    "Completed Activities": "rich_text",
    "Complete": "checkbox",
    "Week": "rich_text",
    "Weekly Planned Miles": "number",
    "Weekly Actual Miles": "number",
    "Sleep Hours": "number",
    "Sleep Status": "select",
    "Weekly Run Goals Met": "number",
    "Weekly Run Goals Planned": "number",
    "Weekly Strength Completed": "number",
    "Weekly Strength Planned": "number",
    "Weekly Avg Sleep": "number",
    "Weekly Sleep Goals Met": "number",
    "Weekly Summary": "rich_text",
}


def validate_schema(notion_client: NotionClient, database_id: str) -> None:
    data_source = notion_client.data_sources.retrieve(data_source_id=database_id)
    properties = data_source.get("properties", {})
    problems = []
    for name, expected_type in CALENDAR_PROPERTIES.items():
        actual_type = (properties.get(name) or {}).get("type")
        if actual_type != expected_type:
            problems.append(f"{name} ({expected_type})")
    if problems:
        raise ValueError(
            "Training Calendar database is missing required properties: "
            + ", ".join(problems)
            + ". See the Training Calendar section in README.md."
        )


def query_calendar_pages(
    notion_client: NotionClient, database_id: str, start: date, end: date
) -> dict[date, dict[str, Any]]:
    pages: dict[date, dict[str, Any]] = {}
    cursor = None
    while True:
        response = notion_client.data_sources.query(
            data_source_id=database_id,
            filter={
                "and": [
                    {"property": "Date", "date": {"on_or_after": start.isoformat()}},
                    {"property": "Date", "date": {"on_or_before": end.isoformat()}},
                ]
            },
            start_cursor=cursor,
        )
        for page in response.get("results", []):
            raw_date = (
                (page.get("properties", {}).get("Date") or {}).get("date") or {}
            ).get("start")
            if raw_date:
                pages.setdefault(date.fromisoformat(raw_date[:10]), page)
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return pages


def day_label(day: date, complete: bool = False) -> str:
    label = day.strftime("%a, %b %d").replace(" 0", " ")
    return f"✅ {label}" if complete else label


def create_missing_days(
    notion_client: NotionClient,
    database_id: str,
    pages: dict[date, dict[str, Any]],
    start: date,
    end: date,
) -> None:
    for day in dates_in_range(start, end):
        if day in pages:
            continue
        notion_client.pages.create(
            parent={"data_source_id": database_id},
            properties={
                "Day": {"title": [{"text": {"content": day_label(day)}}]},
                "Date": {"date": {"start": day.isoformat()}},
                "Miles Planned": {"number": 0},
            },
        )


def number_property(page: dict[str, Any], name: str) -> float:
    value = (page.get("properties", {}).get(name) or {}).get("number")
    return float(value or 0)


def rich_text_property(value: str) -> dict[str, list[dict[str, Any]]]:
    if not value:
        return {"rich_text": []}
    return {"rich_text": [{"text": {"content": value[:2000]}}]}


def get_scheduled_workouts(
    garmin_client: GarminClient, year: int, month: int
) -> dict[date, list[dict[str, str]]]:
    scheduled: dict[date, list[dict[str, str]]] = defaultdict(list)
    workout_type_cache: dict[str, str] = {}
    payload = garmin_client.get_scheduled_workouts(year, month)
    for workout in parse_scheduled_workouts(payload):
        try:
            workout_date = date.fromisoformat(workout["date"])
        except ValueError:
            continue
        workout_id = workout["workout_id"]
        if not workout["sport_key"] and workout_id:
            if workout_id not in workout_type_cache:
                details = garmin_client.get_workout_by_id(workout_id)
                sport = details.get("sportType") or {}
                workout_type_cache[workout_id] = str(
                    sport.get("sportTypeKey") or sport.get("typeKey") or ""
                )
            workout["sport_key"] = workout_type_cache[workout_id]
        scheduled[workout_date].append(workout)
    return dict(scheduled)


def get_sleep_by_date(
    notion_client: NotionClient,
    database_id: str | None,
    start: date,
    end: date,
) -> dict[date, float]:
    if not database_id:
        return {}
    sleep_by_date: dict[date, float] = {}
    cursor = None
    while True:
        response = notion_client.data_sources.query(
            data_source_id=database_id,
            filter={
                "and": [
                    {
                        "property": "Long Date",
                        "date": {"on_or_after": start.isoformat()},
                    },
                    {
                        "property": "Long Date",
                        "date": {"on_or_before": end.isoformat()},
                    },
                ]
            },
            start_cursor=cursor,
        )
        for page in response.get("results", []):
            properties = page.get("properties", {})
            raw_date = ((properties.get("Long Date") or {}).get("date") or {}).get(
                "start"
            )
            hours = (properties.get("Total Sleep (h)") or {}).get("number")
            if raw_date and hours:
                sleep_by_date[date.fromisoformat(raw_date[:10])] = float(hours)
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return sleep_by_date


def update_calendar(
    notion_client: NotionClient,
    garmin_client: GarminClient,
    database_id: str,
    today: date,
    sleep_database_id: str | None = None,
) -> None:
    start, end = month_bounds(today)
    validate_schema(notion_client, database_id)
    pages = query_calendar_pages(notion_client, database_id, start, end)
    create_missing_days(notion_client, database_id, pages, start, end)
    pages = query_calendar_pages(notion_client, database_id, start, end)

    activities = garmin_client.get_activities_by_date(
        start.isoformat(), end.isoformat()
    )
    activity_summaries = summarize_activities(activities)
    scheduled = get_scheduled_workouts(garmin_client, today.year, today.month)
    sleep_by_day = get_sleep_by_date(
        notion_client, sleep_database_id, start, end
    )

    planned_by_day = {
        day: number_property(page, "Miles Planned") for day, page in pages.items()
    }
    weekly_planned: dict[date, float] = defaultdict(float)
    weekly_actual: dict[date, float] = defaultdict(float)
    weekly_run_planned: dict[date, int] = defaultdict(int)
    weekly_run_met: dict[date, int] = defaultdict(int)
    weekly_strength_planned: dict[date, int] = defaultdict(int)
    weekly_strength_completed: dict[date, int] = defaultdict(int)
    weekly_sleep_total: dict[date, float] = defaultdict(float)
    weekly_sleep_days: dict[date, int] = defaultdict(int)
    weekly_sleep_met: dict[date, int] = defaultdict(int)
    for day in dates_in_range(start, end):
        week_start = day - timedelta(days=day.weekday())
        planned_miles = planned_by_day.get(day, 0)
        actual = activity_summaries.get(day, {})
        actual_miles = float(actual.get("run_miles", 0))
        weekly_planned[week_start] += planned_miles
        weekly_actual[week_start] += actual_miles
        if planned_miles > 0:
            weekly_run_planned[week_start] += 1
            if actual_miles + 0.005 >= planned_miles:
                weekly_run_met[week_start] += 1

        planned_strength = sum(
            activity_category(workout.get("sport_key"), workout.get("name", ""))
            == "strength"
            for workout in scheduled.get(day, [])
        )
        actual_strength = int(
            (actual.get("category_counts") or {}).get("strength", 0)
        )
        weekly_strength_planned[week_start] += planned_strength
        weekly_strength_completed[week_start] += min(
            planned_strength, actual_strength
        )

        sleep_hours = sleep_by_day.get(day)
        if sleep_hours is not None:
            weekly_sleep_total[week_start] += sleep_hours
            weekly_sleep_days[week_start] += 1
            if sleep_hours >= 7:
                weekly_sleep_met[week_start] += 1

    for day, page in pages.items():
        actual = activity_summaries.get(
            day,
            {
                "run_miles": 0,
                "categories": set(),
                "category_counts": {},
                "names": [],
            },
        )
        workouts = scheduled.get(day, [])
        planned_miles = planned_by_day.get(day, 0)
        actual_miles = float(actual["run_miles"])
        workout_text, workout_complete = format_planned_workouts(
            workouts, actual.get("category_counts") or {}
        )
        has_run_goal = planned_miles > 0
        run_goal_met = has_run_goal and actual_miles + 0.005 >= planned_miles
        has_plan = has_run_goal or bool(workouts)
        complete = (
            has_plan
            and (not has_run_goal or run_goal_met)
            and (not workouts or workout_complete)
        )
        week_start = day - timedelta(days=day.weekday())
        week_end = week_start + timedelta(days=6)
        summary_day = min(week_end, end)
        sleep_hours = sleep_by_day.get(day)
        sleep_days = weekly_sleep_days[week_start]
        average_sleep = (
            weekly_sleep_total[week_start] / sleep_days if sleep_days else 0
        )
        summary = ""
        if day == summary_day and week_start <= today:
            summary = weekly_summary(
                weekly_actual[week_start],
                weekly_planned[week_start],
                weekly_run_met[week_start],
                weekly_run_planned[week_start],
                weekly_strength_completed[week_start],
                weekly_strength_planned[week_start],
                average_sleep,
                weekly_sleep_met[week_start],
                sleep_days,
            )
        title = day_label(day, complete)
        notion_client.pages.update(
            page_id=page["id"],
            properties={
                "Day": {
                    "title": [
                        {
                            "text": {"content": title},
                            "annotations": {"strikethrough": complete},
                        }
                    ]
                },
                "Miles Run": {"number": round(actual_miles, 2)},
                "Workout Planned": rich_text_property(workout_text),
                "Completed Activities": rich_text_property("; ".join(actual["names"])),
                "Complete": {"checkbox": complete},
                "Week": rich_text_property(f"{week_start:%b %d}–{week_end:%b %d}"),
                "Weekly Planned Miles": {
                    "number": round(weekly_planned[week_start], 2)
                },
                "Weekly Actual Miles": {"number": round(weekly_actual[week_start], 2)},
                "Sleep Hours": {
                    "number": round(sleep_hours, 2)
                    if sleep_hours is not None
                    else None
                },
                "Sleep Status": {
                    "select": {"name": sleep_status(sleep_hours)}
                    if sleep_status(sleep_hours)
                    else None
                },
                "Weekly Run Goals Met": {
                    "number": weekly_run_met[week_start]
                },
                "Weekly Run Goals Planned": {
                    "number": weekly_run_planned[week_start]
                },
                "Weekly Strength Completed": {
                    "number": weekly_strength_completed[week_start]
                },
                "Weekly Strength Planned": {
                    "number": weekly_strength_planned[week_start]
                },
                "Weekly Avg Sleep": {"number": round(average_sleep, 2)},
                "Weekly Sleep Goals Met": {
                    "number": weekly_sleep_met[week_start]
                },
                "Weekly Summary": rich_text_property(summary),
            },
        )


def main() -> None:
    load_dotenv()
    database_id = os.getenv("NOTION_CALENDAR_DB_ID")
    if not database_id:
        print("NOTION_CALENDAR_DB_ID is not set; skipping Training Calendar sync.")
        return

    timezone_name = os.getenv("TRAINING_CALENDAR_TIMEZONE", "America/New_York")
    today = datetime.now(ZoneInfo(timezone_name)).date()
    garmin_client, _ = get_garmin_client()
    notion_client, notion_dbs = get_notion_client()
    update_calendar(
        notion_client,
        garmin_client,
        database_id,
        today,
        notion_dbs.sleep,
    )
    print(f"Training Calendar synced for {today:%B %Y}.")


if __name__ == "__main__":
    main()
