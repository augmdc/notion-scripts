import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from notion_client import Client

NOTION_TOKEN      = os.environ["NOTION_TOKEN"]
AUTOMATIONS_PAGE  = "321b9483a96281faa6a3cc1f6988bdd9"
DRAFTS_DIR        = Path.home() / "Documents/Atlas/Content Lab/1. Production Pipeline/10. Drafts"
STALE_DAYS        = 14

notion = Client(auth=NOTION_TOKEN)


def get_stale_drafts() -> list[tuple[str, int]]:
    """Return (filename, days_since_edit) for drafts idle for STALE_DAYS+ days."""
    cutoff = time.time() - (STALE_DAYS * 86400)
    stale = []
    for f in sorted(DRAFTS_DIR.glob("*.md")):
        mtime = f.stat().st_mtime
        if mtime < cutoff:
            days_idle = int((time.time() - mtime) / 86400)
            stale.append((f.stem, days_idle))
    return stale


def post_nudge(stale: list[tuple[str, int]]) -> None:
    lines = [f"• {name} ({days}d idle)" for name, days in stale]
    message = (
        f"📝 Content Lab nudge — {len(stale)} draft(s) idle for {STALE_DAYS}+ days:\n\n"
        + "\n".join(lines)
    )
    notion.comments.create(
        parent={"page_id": AUTOMATIONS_PAGE},
        rich_text=[{"text": {"content": message}}]
    )
    print(f"Posted nudge: {len(stale)} stale draft(s)")
    for name, days in stale:
        print(f"  {name} ({days}d)")


if __name__ == "__main__":
    print(f"Scanning: {DRAFTS_DIR}")
    stale = get_stale_drafts()
    if not stale:
        print("No stale drafts — all clear.")
    else:
        post_nudge(stale)
