from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from notion_client import Client as NotionClient

from src.helpers import get_garmin_client, get_notion_client
from src.helpers._strength_log import is_strength_activity, normalize_exercise_sets


def rich_text(value: str) -> dict[str, list[dict[str, Any]]]:
    return {"rich_text": [{"text": {"content": value[:2000]}}]} if value else {"rich_text": []}


def find_set(notion_client: NotionClient, database_id: str, set_key: str) -> dict | None:
    response = notion_client.data_sources.query(
        data_source_id=database_id,
        filter={"property": "Set Key", "rich_text": {"equals": set_key}},
    )
    results = response.get("results", [])
    return results[0] if results else None


def properties_for_set(row: dict[str, Any]) -> dict[str, Any]:
    title = f"{row['exercise']} · Set {row['set_number']}"
    return {
        "Set": {"title": [{"text": {"content": title}}]},
        "Date": {"date": {"start": row["date"]}},
        "Workout": rich_text(row["workout"]),
        "Exercise": rich_text(row["exercise"]),
        "Set Number": {"number": row["set_number"]},
        "Set Type": {"select": {"name": row["set_type"]}},
        "Reps": {"number": row["reps"]},
        "Weight (lb)": {"number": row["weight_lb"]},
        "Volume (lb)": {"number": row["volume_lb"]},
        "Duration (sec)": {"number": row["duration_sec"]},
        "Activity ID": rich_text(row["activity_id"]),
        "Set Key": rich_text(row["set_key"]),
    }


def sync_strength_log(
    notion_client: NotionClient, garmin_client: Any, database_id: str, limit: int
) -> tuple[int, int]:
    created = 0
    updated = 0
    for activity in garmin_client.get_activities(0, limit):
        if not is_strength_activity(activity):
            continue
        activity_id = activity.get("activityId")
        if not activity_id:
            continue
        try:
            payload = garmin_client.get_activity_exercise_sets(activity_id)
        except Exception as error:  # Keep other Garmin workflows running.
            print(f"Could not retrieve strength sets for activity {activity_id}: {error}")
            continue
        for row in normalize_exercise_sets(activity, payload):
            properties = properties_for_set(row)
            existing = find_set(notion_client, database_id, row["set_key"])
            if existing:
                notion_client.pages.update(page_id=existing["id"], properties=properties)
                updated += 1
            else:
                notion_client.pages.create(
                    parent={"data_source_id": database_id}, properties=properties
                )
                created += 1
    return created, updated


def main() -> None:
    load_dotenv()
    database_id = os.getenv("NOTION_STRENGTH_DB_ID")
    if not database_id:
        print("NOTION_STRENGTH_DB_ID is not set; skipping Strength Log sync.")
        return
    limit = int(
        os.getenv(
            "GARMIN_STRENGTH_FETCH_LIMIT",
            os.getenv("GARMIN_ACTIVITIES_FETCH_LIMIT", "10"),
        )
    )
    garmin_client, _ = get_garmin_client()
    notion_client, _ = get_notion_client()
    created, updated = sync_strength_log(
        notion_client, garmin_client, database_id, limit
    )
    print(f"Strength Log synced: {created} sets created, {updated} sets updated.")


if __name__ == "__main__":
    main()
