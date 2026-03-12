import os
from datetime import datetime, timedelta, timezone
from notion_client import Client

NOTION_TOKEN      = os.environ["NOTION_TOKEN"]
WEEKLY_REVIEW_DB  = os.environ["WEEKLY_REVIEW_DB_ID"]
TASKS_DB          = "248b9483a9628087ba28000b0963d1e5"

notion = Client(auth=NOTION_TOKEN)


def get_week_label() -> str:
    today = datetime.now(timezone.utc)
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    monday = today + timedelta(days=days_until_monday)
    return monday.strftime("Week of %b %-d")


def get_completed_tasks() -> list[str]:
    """Return names of tasks marked Done in the last 7 days."""
    one_week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    results = notion.databases.query(
        database_id=TASKS_DB,
        filter={
            "and": [
                {"property": "Status", "status": {"equals": "Done"}},
                {"timestamp": "last_edited_time", "last_edited_time": {"after": one_week_ago}}
            ]
        }
    )
    tasks = []
    for page in results["results"]:
        title_parts = page["properties"].get("Name", {}).get("title", [])
        if title_parts:
            tasks.append(title_parts[0]["plain_text"])
    return tasks


def find_weekly_review(label: str) -> str | None:
    results = notion.databases.query(
        database_id=WEEKLY_REVIEW_DB,
        filter={"property": "Week", "title": {"equals": label}}
    )
    if results["results"]:
        return results["results"][0]["id"]
    return None


def prefill(page_id: str, tasks: list[str]) -> None:
    if not tasks:
        print("No completed tasks this week — skipping prefill.")
        return

    lines = [f"• {t}" for t in tasks[:15]]  # cap at 15
    summary = f"{len(tasks)} task(s) completed this week:\n" + "\n".join(lines)

    notion.pages.update(
        page_id=page_id,
        properties={
            "What Moved": {
                "rich_text": [{"text": {"content": summary}}]
            }
        }
    )
    print(f"Pre-filled 'What Moved' with {len(tasks)} task(s).")


if __name__ == "__main__":
    label = get_week_label()
    print(f"Pre-filling: {label}")

    tasks = get_completed_tasks()
    print(f"Found {len(tasks)} completed task(s) in the last 7 days.")

    page_id = find_weekly_review(label)
    if page_id:
        prefill(page_id, tasks)
    else:
        print("Weekly review not found — run create_weekly_review.py first.")
