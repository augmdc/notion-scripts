# CLAUDE.md — notion-scripts

## Overview

GitHub Actions automations that manage Augustin's Notion workspace (Daily Focus, Weekly Review, Shift Report, Content Lab nudges, task allocations).

## Conventions

### Time Format
- Use **24-hour time** in all code, comments, commit messages, and Notion content (e.g., `09:00`, `14:30`, `20:00` — never `9:00 AM`, `2:30 PM`, `8:00 PM`).

### Timezone Handling
- All scripts must use `zoneinfo.ZoneInfo("America/New_York")` for Eastern Time. This handles EST/EDT transitions automatically.
- **Never** hardcode UTC offsets (`timedelta(hours=-5)`). DST makes them wrong half the year.
- GitHub Actions cron only supports UTC. When setting cron schedules:
  - Calculate the UTC time for the **EDT** offset (UTC-4), since that is the "later" variant.
  - Document both EDT and EST mappings in the cron comment.
  - Example: `# Every day at 05:00 ET (09:00 UTC during EDT, 10:00 UTC during EST)`

### Scripts
- All scripts are idempotent — safe to re-run or trigger manually.
- Secrets are managed in repo Settings > Secrets > Actions.
- Python 3.12+, dependencies in `requirements.txt`.
