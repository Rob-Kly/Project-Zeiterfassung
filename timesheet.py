import os
import json
from datetime import datetime, timedelta
from calendar import monthrange
from zfa_utils import load_userlist, load_timestamps, seconds_to_hours_minutes_str


def get_worked_hours(user_id: str, start_date: str, end_date: str) -> dict:
    """Berechnet die geleisteten Arbeitsstunden eines Nutzers im angegebenen Zeitraum."""
    userlist = load_userlist()
    if user_id not in userlist:
        return {"error": f"Unbekannte User-ID {user_id}"}

    user_data = userlist[user_id]
    user_folder = user_data["folder"]
    timestamps_path = os.path.join(user_folder, f"{user_folder}_timestamps.txt")
    timestamps = load_timestamps(timestamps_path)

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

    total_seconds = 0
    details = {}
    current_in = None

    for entry in timestamps:
        ts_time = datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")

        if not (start_dt <= ts_time < end_dt):
            continue

        if entry["type"] == "in":
            current_in = ts_time
        elif entry["type"] == "out" and current_in:
            worked = (ts_time - current_in).total_seconds()
            total_seconds += worked
            day_str = current_in.strftime("%Y-%m-%d")
            details[day_str] = details.get(day_str, 0) + worked / 3600
            current_in = None

    return {
        "user_id": user_id,
        "name": f"{user_data['first_name']} {user_data['last_name']}",
        "total_hours": round(total_seconds / 3600, 2),
        "total_hm": seconds_to_hours_minutes_str(total_seconds),
        "details": [
            {
                "date": d,
                "worked_hours": round(h, 2),
                "worked_hm": seconds_to_hours_minutes_str(h * 3600)
            }
            for d, h in sorted(details.items())
        ]
    }


def get_monthly_report(year: int, month: int) -> dict:
    """Erstellt eine Übersicht aller Nutzer mit ihren Arbeitsstunden für einen Monat."""
    start_date = f"{year}-{month:02d}-01"
    last_day = monthrange(year, month)[1]
    end_date = f"{year}-{month:02d}-{last_day:02d}"

    userlist = load_userlist()
    report = {}

    for user_id in userlist.keys():
        report[user_id] = get_worked_hours(user_id, start_date, end_date)

    return {"year": year, "month": month, "users": report}


def export_monthly_report_json(year: int, month: int) -> str:
    """Exportiert den Monatsreport aller Nutzer als JSON-formatierte TXT-Datei im Ordner 'reports/'."""
    report = get_monthly_report(year, month)

    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    filename = os.path.join(reports_dir, f"monthly_report_{year}_{month:02d}.txt")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    return f"Monatsreport {month:02d}/{year} wurde nach '{filename}' exportiert."
