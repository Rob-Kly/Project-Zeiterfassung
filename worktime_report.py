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
def get_pending_corrections_for_user(user_id):
    """
    Gibt alle automatischen Einträge eines Nutzers zurück,
    die noch nicht bestätigt wurden.
    """
    userlist = load_userlist()
    if user_id not in userlist:
        return []

    user = userlist[user_id]
    folder = user["folder"]
    path = os.path.join(folder, f"{folder}_timestamps.txt")
    timestamps = load_timestamps(path)

    results = []

    for entry in timestamps:
        # Nur automatische Einträge
        if not entry.get("auto"):
            continue

        # Bereits bearbeitet/akzeptiert → ignorieren
        if entry.get("auto_confirmed"):
            continue

        # Datum extrahieren
        try:
            dt = datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")
        except:
            continue

        results.append({
            "date": dt.strftime("%Y-%m-%d"),
            "type": entry.get("type")
        })

    return results



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
