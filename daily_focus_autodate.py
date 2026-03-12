import os
from datetime import datetime, timedelta, timezone
from notion_client import Client

NOTION_TOKEN       = os.environ["NOTION_TOKEN"]
DAILY_FOCUS_PAGE_ID = "2d8b9483a962803c9564fbae0c35ffd3"

notion = Client(auth=NOTION_TOKEN)


def get_today_label() -> str:
    """Returns 'Mon DD' in Eastern time."""
    eastern = datetime.now(timezone.utc) - timedelta(hours=5)  # EST (UTC-5)
    return eastern.strftime("%b %-d")


def update_date():
    today = get_today_label()
    new_title = f"💡 Daily Focus — {today}"

    page = notion.pages.retrieve(page_id=DAILY_FOCUS_PAGE_ID)
    current = ""
    title_prop = page["properties"].get("title", {}).get("title", [])
    if title_prop:
        current = title_prop[0]["plain_text"]

    if today in current:
        print(f"Already up to date: {current}")
        return

    notion.pages.update(
        page_id=DAILY_FOCUS_PAGE_ID,
        properties={
            "title": {"title": [{"text": {"content": new_title}}]}
        }
    )
    print(f"Updated to: {new_title}")


if __name__ == "__main__":
    update_date()
