import os
from datetime import datetime, timedelta, timezone
from notion_client import Client

NOTION_TOKEN      = os.environ["NOTION_TOKEN"]
WEEKLY_REVIEW_DB  = os.environ["WEEKLY_REVIEW_DB_ID"]

notion = Client(auth=NOTION_TOKEN)


def get_week_label() -> str:
    """Returns the label for the current week (coming Monday from Sunday evening)."""
    today = datetime.now(timezone.utc)
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    monday = today + timedelta(days=days_until_monday)
    return monday.strftime("Week of %b %-d")


def find_weekly_review(label: str) -> str | None:
    results = notion.databases.query(
        database_id=WEEKLY_REVIEW_DB,
        filter={"property": "Week", "title": {"equals": label}}
    )
    if results["results"]:
        return results["results"][0]["id"]
    return None


def add_reminder(page_id: str) -> None:
    notion.comments.create(
        parent={"page_id": page_id},
        rich_text=[{
            "text": {
                "content": "⏰ Shift Report time. 15 minutes. Fill this in before bed."
            }
        }]
    )
    print(f"Reminder comment added to {page_id}")


if __name__ == "__main__":
    label = get_week_label()
    print(f"Looking for weekly review: {label}")

    page_id = find_weekly_review(label)
    if page_id:
        add_reminder(page_id)
    else:
        print("Weekly review entry not found — skipping.")
