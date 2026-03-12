import os
from datetime import datetime, timedelta, timezone
from notion_client import Client

# ---- ENV VARS ----
NOTION_TOKEN      = os.environ["NOTION_TOKEN"]
WEEKLY_REVIEW_DB  = os.environ["WEEKLY_REVIEW_DB_ID"]  # Weekly Review database ID

notion = Client(auth=NOTION_TOKEN)


def get_week_label() -> str:
    """Returns 'Week of Mon DD' for the coming Monday (start of the work week)."""
    today = datetime.now(timezone.utc)
    # Run on Sunday — label the week that starts tomorrow (Monday)
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    monday = today + timedelta(days=days_until_monday)
    return monday.strftime("Week of %b %-d")


def week_entry_exists(label: str) -> bool:
    """Check if an entry for this week already exists."""
    results = notion.databases.query(
        database_id=WEEKLY_REVIEW_DB,
        filter={
            "property": "Week",
            "title": {"equals": label}
        }
    )
    return len(results["results"]) > 0


def create_weekly_entry(label: str) -> None:
    """Create a new Weekly Review entry."""
    notion.pages.create(
        parent={"database_id": WEEKLY_REVIEW_DB},
        properties={
            "Week": {
                "title": [{"text": {"content": label}}]
            }
        }
    )
    print(f"Created: {label}")


if __name__ == "__main__":
    label = get_week_label()
    print(f"Checking for: {label}")

    if week_entry_exists(label):
        print(f"Already exists — skipping.")
    else:
        create_weekly_entry(label)
