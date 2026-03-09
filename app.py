import os
import time
import logging
import threading
import requests
from flask import Flask, Response
from icalendar import Calendar

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)
cached_ical = None
cache_lock = threading.Lock()

def get_calendars():
    calendars = []
    i = 1
    while True:
        url = os.environ.get(f"CALENDAR_{i}_URL")
        if not url:
            break
        name = os.environ.get(f"CALENDAR_{i}_NAME", f"Calendar {i}")
        calendars.append({"url": url, "name": name})
        i += 1
    return calendars

def get_filters():
    raw = os.environ.get("FILTER_OUT", "")
    if not raw:
        return []
    return [f.strip() for f in raw.split(",") if f.strip()]

def should_filter(component, filters):
    if not filters:
        return False
    summary = str(component.get('SUMMARY', ''))
    return any(f.lower() in summary.lower() for f in filters)

def fetch_and_merge():
    global cached_ical
    calendars = get_calendars()
    if not calendars:
        log.warning("No calendars configured!")
        return

    filters = get_filters()
    if filters:
        log.info(f"Filtering out events containing: {filters}")

    merged = Calendar()
    merged.add('prodid', '-//ical-merger//EN')
    merged.add('version', '2.0')
    merged.add('x-wr-calname', 'Merged Calendar')

    seen_uids = set()
    seen_timezones = set()

    for cal in calendars:
        log.info(f"Fetching {cal['name']} from {cal['url']}")
        try:
            resp = requests.get(cal['url'], timeout=60)
            resp.raise_for_status()
            source = Calendar.from_ical(resp.text)
            for component in source.walk():
                if component.name == "VTIMEZONE":
                    tzid = str(component.get('TZID', ''))
                    if tzid not in seen_timezones:
                        seen_timezones.add(tzid)
                        merged.add_component(component)
                elif component.name == "VEVENT":
                    if should_filter(component, filters):
                        log.info(f"Filtered out: {component.get('SUMMARY', '')}")
                        continue
                    uid = str(component.get('UID', ''))
                    if uid not in seen_uids:
                        seen_uids.add(uid)
                        merged.add_component(component)
        except Exception as e:
            log.error(f"Failed to fetch {cal['name']}: {e}")

    with cache_lock:
        cached_ical = merged.to_ical()
    log.info("Merge complete.")

def background_refresh():
    interval = int(os.environ.get("REFRESH_INTERVAL", 900))
    while True:
        try:
            fetch_and_merge()
        except Exception as e:
            log.error(f"Refresh error: {e}")
        time.sleep(interval)

@app.route("/calendar.ics")
def serve_calendar():
    with cache_lock:
        data = cached_ical
    if data is None:
        return Response("Not ready yet.", status=503)
    return Response(data, mimetype="text/calendar")

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    fetch_and_merge()
    t = threading.Thread(target=background_refresh, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
