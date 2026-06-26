import csv
import json
import os
import urllib.request
from datetime import datetime, timezone

RECORD_ID = "20260147"
ZENODO_API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"

DATA_DIR = "data"
SNAPSHOT_FILE = os.path.join(DATA_DIR, "magbridge_zenodo_snapshots.csv")
DAILY_FILE = os.path.join(DATA_DIR, "magbridge_zenodo_daily.csv")

os.makedirs(DATA_DIR, exist_ok=True)

today = datetime.now(timezone.utc).date().isoformat()

request = urllib.request.Request(
    ZENODO_API_URL,
    headers={
        "User-Agent": "MagBridge-Battery-Zenodo-Stats-Tracker/1.0"
    },
)

with urllib.request.urlopen(request, timeout=30) as response:
    record = json.loads(response.read().decode("utf-8"))

stats = record.get("stats", {})
metadata = record.get("metadata", {})

row = {
    "date": today,
    "record_id": RECORD_ID,
    "doi": metadata.get("doi", ""),
    "title": metadata.get("title", ""),
    "views": int(stats.get("views", 0) or 0),
    "unique_views": int(stats.get("unique_views", 0) or 0),
    "downloads": int(stats.get("downloads", 0) or 0),
    "unique_downloads": int(stats.get("unique_downloads", 0) or 0),
    "version_views": int(stats.get("version_views", 0) or 0),
    "version_unique_views": int(stats.get("version_unique_views", 0) or 0),
    "version_downloads": int(stats.get("version_downloads", 0) or 0),
    "version_unique_downloads": int(stats.get("version_unique_downloads", 0) or 0),
    "volume": int(stats.get("volume", 0) or 0),
    "version_volume": int(stats.get("version_volume", 0) or 0),
    "snapshot_utc": datetime.now(timezone.utc).isoformat(),
}

fieldnames = list(row.keys())

existing_rows = []

if os.path.exists(SNAPSHOT_FILE):
    with open(SNAPSHOT_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)

# Avoid duplicate rows when the workflow is run multiple times on the same day.
updated = False
for i, old_row in enumerate(existing_rows):
    if old_row.get("date") == today:
        existing_rows[i] = {key: str(value) for key, value in row.items()}
        updated = True
        break

if not updated:
    existing_rows.append({key: str(value) for key, value in row.items()})

existing_rows = sorted(existing_rows, key=lambda x: x["date"])

with open(SNAPSHOT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(existing_rows)

# Build daily delta file
daily_rows = []
previous = None

numeric_fields = [
    "views",
    "unique_views",
    "downloads",
    "unique_downloads",
    "version_views",
    "version_unique_views",
    "version_downloads",
    "version_unique_downloads",
    "volume",
    "version_volume",
]

for current in existing_rows:
    daily = {
        "date": current["date"],
        "record_id": current["record_id"],
    }

    for field in numeric_fields:
        current_value = int(current.get(field, 0) or 0)

        if previous is None:
            delta = 0
        else:
            previous_value = int(previous.get(field, 0) or 0)
            delta = current_value - previous_value

        daily[f"daily_{field}"] = delta
        daily[f"cumulative_{field}"] = current_value

    daily_rows.append(daily)
    previous = current

daily_fieldnames = list(daily_rows[0].keys()) if daily_rows else []

with open(DAILY_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=daily_fieldnames)
    writer.writeheader()
    writer.writerows(daily_rows)

print("Zenodo snapshot saved.")
print(json.dumps(row, indent=2))
