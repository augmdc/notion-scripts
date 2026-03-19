import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from notion_client import Client

NOTION_TOKEN      = os.environ["NOTION_TOKEN"]
WEEKLY_REVIEW_DB  = os.environ["WEEKLY_REVIEW_DB_ID"]
TASKS_DB          = "248b9483a9628087ba28000b0963d1e5"

notion = Client(auth=NOTION_TOKEN)


def get_week_label() -> str:
    today = datetime.now(ZoneInfo("America/New_York"))
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    monday = today + timedelta(days=days_until_monday)
    return monday.strftime("Week of %b %-d")


def get_week_bounds() -> tuple[str, str]:
    """Return ISO strings for last Monday 00:00 and today 23:59 (Sunday)."""
    today = datetime.now(ZoneInfo("America/New_York")).replace(hour=23, minute=59, second=59)
    last_monday = (today - timedelta(days=6)).replace(hour=0, minute=0, second=0)
    return last_monday.isoformat(), today.isoformat()


def get_completed_tasks() -> dict[str, list[str]]:
    """Return tasks marked Done with a due date in the past week, grouped by track."""
    week_start, week_end = get_week_bounds()

    results = notion.databases.query(
        database_id=TASKS_DB,
        filter={
            "and": [
                {"property": "Status", "status": {"equals": "Done"}},
                {"property": "Due Date", "date": {"on_or_after": week_start[:10]}},
                {"property": "Due Date", "date": {"on_or_before": week_end[:10]}}
            ]
        }
    )

    by_track: dict[str, list[str]] = {"PhD": [], "AI Learning": [], "Other": []}
    for page in results["results"]:
        title_parts = page["properties"].get("Name", {}).get("title", [])
        name = title_parts[0]["plain_text"] if title_parts else "(untitled)"

        track_prop = page["properties"].get("Track", {}).get("select")
        track = track_prop["name"] if track_prop else "Other"
        if track not in by_track:
            track = "Other"

        by_track[track].append(name)

    return by_track


def find_weekly_review(label: str) -> str | None:
    results = notion.databases.query(
        database_id=WEEKLY_REVIEW_DB,
        filter={"property": "Week", "title": {"equals": label}}
    )
    if results["results"]:
        return results["results"][0]["id"]
    return None


def prefill(page_id: str, by_track: dict[str, list[str]]) -> None:
    total = sum(len(v) for v in by_track.values())
    if total == 0:
        print("No completed tasks with due dates this week — skipping prefill.")
        return

    lines = []
    for track, tasks in by_track.items():
        if tasks:
            lines.append(f"{track}:")
            lines.extend(f"  • {t}" for t in tasks)
            lines.append("")

    summary = f"{total} task(s) completed this week:\n\n" + "\n".join(lines).rstrip()

    notion.pages.update(
        page_id=page_id,
        properties={
            "What Moved": {
                "rich_text": [{"text": {"content": summary}}]
            }
        }
    )
    print(f"Pre-filled 'What Moved' with {total} task(s) across {sum(1 for v in by_track.values() if v)} track(s).")


if __name__ == "__main__":
    label = get_week_label()
    print(f"Pre-filling: {label}")

    by_track = get_completed_tasks()
    total = sum(len(v) for v in by_track.values())
    print(f"Found {total} completed task(s) in the past week.")
    for track, tasks in by_track.items():
        if tasks:
            print(f"  {track}: {len(tasks)}")

    page_id = find_weekly_review(label)
    if page_id:
        prefill(page_id, by_track)
    else:
        print("Weekly review not found — run create_weekly_review.py first.")
