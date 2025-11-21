import os
import json
from datetime import datetime, timedelta
from calendar import monthrange

from zfa_io import load_userlist, load_timestamps, seconds_to_hours_minutes_str
from config import REPORTS_DIR

"""
Funktionen zur Auswertung der Arbeitszeiten und Erstellung von Monatsreports.

Aufgaben:
- Berechnung der geleisteten Arbeitszeit eines Nutzers in einem Zeitraum
- Aggregation aller Nutzer zu einem Monatsreport
- Export eines Monatsreports in eine JSON-formatierte TXT-Datei
"""


# ==========================================================
# ARBEITSZEIT FÜR EINEN NUTZER BERECHNEN
# ==========================================================
def get_worked_hours(user_id: str, start_date: str, end_date: str) -> dict:
    """
    Berechnet die geleisteten Arbeitsstunden eines Nutzers im angegebenen Zeitraum.

    :param user_id: ID des Nutzers (z.B. "1")
    :param start_date: Startdatum (inklusive) im Format "YYYY-MM-DD"
    :param end_date: Enddatum (inklusive) im Format "YYYY-MM-DD"
    :return: Dictionary mit Gesamtzeit und Tages-Details, z.B.:
        {
            "user_id": "1",
            "name": "Max Mustermann",
            "total_hours": 40.0,
            "total_hm": "40h 0m",
            "details": [
                {
                    "date": "2025-11-01",
                    "worked_hours": 8.0,
                    "worked_hm": "8h 0m",
                },
                ...
            ]
        }
    """
    userlist = load_userlist()
    if user_id not in userlist:
        return {"error": f"Unbekannte User-ID {user_id}"}

    user_data = userlist[user_id]
    user_folder = user_data["folder"]
    timestamps_path = os.path.join(user_folder, f"{user_folder}_timestamps.txt")
    timestamps = load_timestamps(timestamps_path)

    # Zeitfenster berechnen (end_date inklusive → +1 Tag)
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

    total_seconds = 0
    details: dict[str, float] = {}
    current_in: datetime | None = None

    for entry in timestamps:
        ts_time = datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")

        # Nur Einträge innerhalb des gewählten Zeitraums berücksichtigen
        if not (start_dt <= ts_time < end_dt):
            continue

        if entry["type"] == "in":
            current_in = ts_time
        elif entry["type"] == "out" and current_in:
            worked = (ts_time - current_in).total_seconds()
            total_seconds += worked

            day_str = current_in.strftime("%Y-%m-%d")
            details[day_str] = details.get(day_str, 0.0) + worked / 3600.0
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
                "worked_hm": seconds_to_hours_minutes_str(h * 3600),
            }
            for d, h in sorted(details.items())
        ],
    }


# ==========================================================
# MONATSREPORT FÜR ALLE NUTZER
# ==========================================================
def get_monthly_report(year: int, month: int) -> dict:
    """
    Erstellt eine Übersicht aller Nutzer mit ihren Arbeitsstunden für einen Monat.

    :param year: Jahr (z.B. 2025)
    :param month: Monat (1–12)
    :return: Dictionary mit allen Nutzern und deren Monatsdaten, z.B.:
        {
            "year": 2025,
            "month": 11,
            "users": {
                "1": { ... Ergebnis von get_worked_hours(...) ... },
                "2": { ... },
                ...
            }
        }
    """
    start_date = f"{year}-{month:02d}-01"
    last_day = monthrange(year, month)[1]
    end_date = f"{year}-{month:02d}-{last_day:02d}"

    userlist = load_userlist()
    report: dict[str, dict] = {}

    for user_id in userlist.keys():
        report[user_id] = get_worked_hours(user_id, start_date, end_date)

    return {"year": year, "month": month, "users": report}


# ==========================================================
# MONATSREPORT EXPORTIEREN
# ==========================================================
def export_monthly_report_json(year: int, month: int) -> str:
    """
    Exportiert den Monatsreport aller Nutzer als JSON-formatierte TXT-Datei.

    Die Datei wird im Ordner REPORTS_DIR abgelegt und erhält den Namen
    "monthly_report_<year>_<month>.txt".
    """
    report = get_monthly_report(year, month)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = os.path.join(REPORTS_DIR, f"monthly_report_{year}_{month:02d}.txt")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    return f"Monatsreport {month:02d}/{year} wurde nach '{filename}' exportiert."


# ==========================================================
# MANUELLER TESTSTARTPUNKT
# ==========================================================
if __name__ == "__main__":
    # Beispiel: aktuellen Monat in der Konsole testen
    today = datetime.now()
    test_report = get_monthly_report(today.year, today.month)
    print(json.dumps(test_report, indent=4, ensure_ascii=False))
