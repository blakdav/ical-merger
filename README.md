# ical-merger

A lightweight Docker container that fetches multiple ICS/iCal calendar feeds, merges them into a single calendar, and serves the result as a single `.ics` URL on your local network.

## How it works

On startup, the container fetches all configured calendar URLs, merges them into one ICS feed, and serves it at `http://your-host:5000/calendar.ics`. It refreshes automatically in the background on a configurable interval.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CALENDAR_1_URL` | Yes | URL of the first ICS feed |
| `CALENDAR_1_NAME` | No | Display name for the first calendar |
| `CALENDAR_2_URL` | No | URL of the second ICS feed |
| `CALENDAR_2_NAME` | No | Display name for the second calendar |
| `CALENDAR_3_URL` | No | URL of the third ICS feed (continue pattern for more) |
| `CALENDAR_3_NAME` | No | Display name for the third calendar |
| `REFRESH_INTERVAL` | No | How often to re-fetch calendars in seconds (default: 900) |
| `FILTER_OUT` | No | Comma-separated list of keywords to exclude events by title (case-insensitive). Example: `FILTER_OUT=8a-5p,Out of Office` |

## Endpoints

- `GET /calendar.ics` — the merged calendar feed
- `GET /health` — returns `OK` if the container is running

## Notes

- Duplicate events (same UID) are automatically deduplicated
- If a calendar feed fails to fetch, it is skipped and the last successful merge is served
- Add as many calendars as needed by continuing the `CALENDAR_N_URL` / `CALENDAR_N_NAME` pattern
