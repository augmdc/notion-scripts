import os
import time
import httpx
from pathlib import Path

NOTION_TOKEN      = os.environ["NOTION_TOKEN"]
AUTOMATIONS_PAGE  = "321b9483a96281faa6a3cc1f6988bdd9"
DRAFTS_DIR        = Path.home() / "Documents/Atlas/Content Lab/1. Production Pipeline/10. Drafts"
STALE_DAYS        = 14

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


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
    from datetime import date
    lines = "\n".join(f"- [ ] {name} ({days}d idle)" for name, days in stale)
    title = f"📝 Stale Drafts — {date.today().strftime('%b %-d')}"
    content = f"These drafts have had no changes for {STALE_DAYS}+ days. Pick one or archive it.\n\n{lines}"

    resp = httpx.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json={
            "parent": {"page_id": AUTOMATIONS_PAGE},
            "properties": {
                "title": {"title": [{"type": "text", "text": {"content": title}}]}
            },
            "children": [{
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            }]
        }
    )
    resp.raise_for_status()
    print(f"Created nudge page: {title}")
    for name, days in stale:
        print(f"  {name} ({days}d)")


if __name__ == "__main__":
    print(f"Scanning: {DRAFTS_DIR}")
    stale = get_stale_drafts()
    if not stale:
        print("No stale drafts — all clear.")
    else:
        post_nudge(stale)
