import os, math
from datetime import datetime, timedelta, timezone
from dateutil.rrule import rrule, WEEKLY, MO
from notion_client import Client

# ---- ENV VARS ----
NOTION_TOKEN   = os.environ["NOTION_TOKEN"]
MASTER_DB_ID   = os.environ["MASTER_DB_ID"]     # Master Tasks DB
WEEKS_DB_ID    = os.environ["WEEKS_DB_ID"]      # Weeks DB
ALLOCS_DB_ID   = os.environ["ALLOCS_DB_ID"]     # Allocations DB
JOBS_DB_ID     = os.environ["JOBS_DB_ID"]       # Jobs DB
RUN_IF_NO_JOB  = os.getenv("RUN_IF_NO_JOB", "false").lower() == "true"

# Property names (edit if yours differ)
P_TASK_NAME    = "Name"
P_TYPE         = "Type"          # Activity / Deliverable
P_START        = "Start"
P_DUE          = "Due"
P_HOURS_EST    = "Hours Est (h)"
P_WEEK_TITLE   = "Week"          # in Weeks DB, title like 2026-[W]05
P_WEEK_START   = "Week Start"    # optional date in Weeks DB

notion = Client(auth=NOTION_TOKEN)

def first_queued_job():
    res = notion.databases.query(database_id=JOBS_DB_ID, filter={
        "and": [
            {"property": "Type", "select": {"equals": "Run Allocations"}},
            {"property": "Status", "select": {"equals": "Queued"}}
        ]
    })
    return res["results"][0] if res["results"] else None

def set_job_status(job_id, status, note=None):
    props = { "Status": { "select": { "name": status } } }
    if status in ("Done", "Error"):
        props["Finished At"] = {"date": {"start": datetime.now(timezone.utc).isoformat()}}
    if note:
        props["Notes"] = { "rich_text": [ { "text": { "content": note[:1900] } } ] }
    notion.pages.update(page_id=job_id, properties=props)

def fetch_weeks_index():
    """Return dicts to find a Week page by Week title or by Week Start date."""
    idx_by_title, idx_by_date = {}, {}
    cursor = None
    while True:
        res = notion.databases.query(database_id=WEEKS_DB_ID, start_cursor=cursor) if cursor else notion.databases.query(database_id=WEEKS_DB_ID)
        for p in res["results"]:
            pid = p["id"]
            # title
            title_items = p["properties"][P_WEEK_TITLE]["title"]
            title = title_items[0]["plain_text"] if title_items else ""
            if title:
                idx_by_title[title] = pid
            # date
            if P_WEEK_START in p["properties"] and p["properties"][P_WEEK_START]["date"]:
                d = p["properties"][P_WEEK_START]["date"]["start"]  # YYYY-MM-DD
                idx_by_date[d] = pid
        if not res.get("has_more"):
            break
        cursor = res["next_cursor"]
    return idx_by_title, idx_by_date

def iso_week_label(dt):
    return dt.strftime("%G-[W]%V")

def mondays_between(start_dt, end_dt):
    # snap to Monday on/after start
    s = start_dt
    if s.weekday() != 0:
        s = s + timedelta(days=(7 - s.weekday()))
    for d in rrule(WEEKLY, byweekday=MO, dtstart=s, until=end_dt):
        yield d

def upsert_allocation(task_id, task_name, week_id, week_label, hours):
    # Search existing Allocation Task×Week
    qry = notion.databases.query(database_id=ALLOCS_DB_ID, filter={
        "and": [
            {"property": "Task", "relation": {"contains": task_id}},
            {"property": "Week", "relation": {"contains": week_id}}
        ]
    })
    if qry["results"]:
        alloc_id = qry["results"][0]["id"]
        notion.pages.update(page_id=alloc_id, properties={
            "Planned Hours (h)": {"number": round(hours, 2)}
        })
        return "updated"
    # else create
    notion.pages.create(parent={"database_id": ALLOCS_DB_ID}, properties={
        "Name": {"title": [{"text": {"content": f"{task_name} · {week_label}"}}]},
        "Task": {"relation": [{"id": task_id}]},
        "Week": {"relation": [{"id": week_id}]} ,
        "Planned Hours (h)": {"number": round(hours, 2)}
    })
    return "created"

def run():
    job = first_queued_job()
    if not job and not RUN_IF_NO_JOB:
        return "No job; exiting."

    if job:
        set_job_status(job["id"], "Running")

    idx_by_title, idx_by_date = fetch_weeks_index()

    # Pull Activities with Start & Due
    cursor = None
    tasks = []
    filter_ = {"and": [
        {"property": P_TYPE, "select": {"equals": "Activity"}},
        {"property": P_START, "date": {"is_not_empty": True}},
        {"property": P_DUE, "date": {"is_not_empty": True}}
    ]}
    while True:
        res = notion.databases.query(database_id=MASTER_DB_ID, filter=filter_, start_cursor=cursor) if cursor \
              else notion.databases.query(database_id=MASTER_DB_ID, filter=filter_)
        tasks.extend(res["results"])
        if not res.get("has_more"): break
        cursor = res["next_cursor"]

    created, updated = 0, 0
    for t in tasks:
        props = t["properties"]
        name_items = props[P_TASK_NAME]["title"]
        name = name_items[0]["plain_text"] if name_items else "(untitled)"

        start_iso = props[P_START]["date"]["start"]
        due_iso   = props[P_DUE]["date"]["start"]
        # Normalize to datetimes
        s = datetime.fromisoformat(start_iso.replace("Z","+00:00"))
        e = datetime.fromisoformat(due_iso.replace("Z","+00:00"))

        est = props.get(P_HOURS_EST, {}).get("number")
        est = float(est) if est is not None else 0.0

        weeks = list(mondays_between(s, e))
        if not weeks:
            weeks = [s]  # single week fallback
        n = max(1, len(weeks))
        per_week = (est / n) if est > 0 else 0.0

        # rounding: push remainder to the last week
        carry = est - round(per_week, 2) * (n - 1)
        for i, w in enumerate(weeks):
            label = iso_week_label(w)
            week_id = idx_by_title.get(label)
            if not week_id and P_WEEK_START in idx_by_date:
                week_id = idx_by_date.get(w.date().isoformat())
            if not week_id:
                # skip if week missing
                continue
            hrs = carry if i == n - 1 and est > 0 else per_week
            res = upsert_allocation(t["id"], name, week_id, label, hrs)
            created += (res == "created")
            updated += (res == "updated")

    if job:
        set_job_status(job["id"], "Done", note=f"Allocations: +{created} / ✎{updated}")
    return f"Done (+{created}, ✎{updated})"

if __name__ == "__main__":
    print(run())
