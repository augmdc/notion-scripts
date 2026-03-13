import os
from datetime import datetime, timedelta, timezone
from notion_client import Client

NOTION_TOKEN        = os.environ["NOTION_TOKEN"]
DAILY_FOCUS_DB      = "aee8c3a1617444378062040092ce5101"

notion = Client(auth=NOTION_TOKEN)

GOAL_AREAS = [
    "Sleep",
    "Deep Work",
    "PhD / Research",
    "Fitness",
    "T-Shape / Learning",
    "Side Project",
    "Social",
    "Creative",
]


def get_today_eastern() -> datetime:
    """Return current datetime in Eastern time (UTC-5, no DST handling needed for daily cron)."""
    return datetime.now(timezone.utc) - timedelta(hours=5)


def entry_exists_today(date_str: str) -> bool:
    """Check if a Daily Focus entry already exists for this date."""
    results = notion.databases.query(
        database_id=DAILY_FOCUS_DB,
        filter={"property": "Day", "date": {"equals": date_str}}
    )
    return len(results["results"]) > 0


def build_blocks() -> list:
    """Build goal area heading + empty todo block for each area."""
    blocks = []
    for area in GOAL_AREAS:
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": area}}]
            },
        })
        blocks.append({
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [],
                "checked": False,
            },
        })
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    blocks.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": "Parking Lot"}}]
        },
    })
    blocks.append({
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [],
        },
    })
    return blocks


def create_entry(label: str, date_str: str) -> None:
    notion.pages.create(
        parent={"database_id": DAILY_FOCUS_DB},
        properties={
            "Date": {"title": [{"text": {"content": label}}]},
            "Day": {"date": {"start": date_str}}
        },
        children=build_blocks(),
    )
    print(f"Created Daily Focus entry: {label}")


if __name__ == "__main__":
    today = get_today_eastern()
    date_str = today.strftime("%Y-%m-%d")
    label = today.strftime("%b %-d")

    print(f"Checking for Daily Focus entry: {label}")

    if entry_exists_today(date_str):
        print("Entry already exists — skipping.")
    else:
        create_entry(label, date_str)
