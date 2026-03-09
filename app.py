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

def fetch_and_merge():
    global cached_ical
    calendars = get_calendars()
    if not calendars:
        log.warning("No calendars configured!")
        return

    merged = Calendar()
    merged.add('prodid', '-//ical-merger//EN')
    merged.add('version', '2.0')
    merged.add('x-wr-calname', 'Merged Calendar')

    for cal in calendars:
        log.info(f"Fetching {cal['name']} from {cal['url']}")
        try:
            resp = requests.get(cal['url'], timeout=15)
            resp.raise_for_status()
            source = Calendar.from_ical(resp.text)
            for component in source.walk():
                if component.name in ("VEVENT", "VTIMEZONE"):
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
```

---

**requirements.txt:**
```
flask==3.1.0
requests==2.32.3
icalendar==6.1.1
```

---

**Dockerfile:**
```
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 5000
CMD ["python", "app.py"]
