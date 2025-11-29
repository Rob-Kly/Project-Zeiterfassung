import os
from datetime import datetime

from zfa_io import (
    load_userlist,
    load_timestamps,
    save_timestamps,
    seconds_to_hours_minutes_str,
)
from zfa_flags import set_pending_corrections_flag

from config import (
    DEFAULT_WORK_START,
    DEFAULT_WORK_END,
    DEFAULT_LATE_LOGIN,
)


"""
Modul für Zeiterfassungs-Buchungen (Kommen/Gehen).

Aufgaben:
- Normale An- und Abmeldung von Nutzern
- Automatische Korrekturen bei vergessenen Logins/Logouts
- Protokollierung von Fehlerfällen in error_log.txt
- Unterstützung von NFC-Buchungen über clock_with_nfc()
- Ermittlung offener automatischer Korrekturen für die Admin-Ansicht
"""

# ==========================================================
# FEHLERPROTOKOLL
# ==========================================================
def log_error(user_id: str, user_name: str, message: str) -> None:
    """
    Schreibt einen Fehlerfall (vergessener Login/Logout etc.)
    mit Zeitstempel in die Datei error_log.txt.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{now} | User {user_id} ({user_name}) | Fehler: {message}\n"
    with open("error_log.txt", "a", encoding="utf-8") as f:
        f.write(entry)


# ==========================================================
# ZEITBUCHUNG (KOMMEN / GEHEN)
# ==========================================================
def clock(user_id):
    """
    Führt eine Kommen-/Gehen-Buchung für den angegebenen Nutzer aus.

    Verhalten:
    - Wenn der letzte Eintrag ein "in" ist:
        - und am Vortag liegt → Auto-Logout am Vortag, neuer Login heute
        - und heute liegt        → normales Logout (mit Dauer)
    - Wenn kein aktiver Login existiert:
        - und heute noch kein "in" und Uhrzeit >= DEFAULT_LATE_LOGIN
              → Auto-Login morgens + Auto-Logout jetzt (beide als auto=True)
        - sonst → normaler Login
    """
    userlist = load_userlist()
    if user_id not in userlist:
        return f"Unbekannte User-ID {user_id}"

    user_data = userlist[user_id]
    user_folder = user_data["folder"]
    os.makedirs(user_folder, exist_ok=True)

    timestamps_path = os.path.join(user_folder, f"{user_folder}_timestamps.txt")
    timestamps = load_timestamps(timestamps_path)

    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    today_str = now_dt.strftime("%Y-%m-%d")

    # Letzten Eintrag bestimmen (falls vorhanden)
    last_entry = timestamps[-1] if timestamps else None
    last_type = last_entry["type"] if last_entry else None

    # ==========================================================
    # Fall A: Letzter Eintrag war "in" → jetzt "out" buchen
    # ==========================================================
    if last_type == "in":
        try:
            last_in = datetime.strptime(last_entry["time"], "%Y-%m-%d %H:%M:%S")
        except (KeyError, ValueError):
            last_in = None

        if last_in is not None and last_in.date() < now_dt.date():
            # Vortag war noch angemeldet → Auto-Logout am DEFAULT_WORK_END
            auto_out = last_in.replace(
                hour=DEFAULT_WORK_END[0],
                minute=DEFAULT_WORK_END[1],
                second=0,
            )
            auto_out_str = auto_out.strftime("%Y-%m-%d %H:%M:%S")

            timestamps.append({
                "time": auto_out_str,
                "type": "out",
                "auto": True,
            })

            # Neuen Arbeitstag mit Login starten
            timestamps.append({
                "time": now_str,
                "type": "in",
                "auto": False,
            })

            save_timestamps(timestamps_path, timestamps)
            set_pending_corrections_flag(True)

            message = (
                f"Nutzer {user_id} ({user_data['first_name']} "
                f"{user_data['last_name']}) hat den Vortag nicht abgemeldet. "
                f"Automatische Abmeldung um {auto_out.strftime('%H:%M')} gesetzt. "
                "Neuer Arbeitstag gestartet (angemeldet)."
            )
            return message
        else:
            # Normales Logout am selben Tag
            if last_in is not None:
                duration = now_dt - last_in
                duration_str = seconds_to_hours_minutes_str(duration.total_seconds())
            else:
                duration_str = "unbekannt"

            timestamps.append({
                "time": now_str,
                "type": "out",
                "auto": False,
            })

            save_timestamps(timestamps_path, timestamps)

            message = (
                f"Nutzer {user_id} ({user_data['first_name']} "
                f"{user_data['last_name']}) hat sich abgemeldet. "
                f"Sitzungslänge: {duration_str}."
            )
            return message

    # ==========================================================
    # Fall B: Kein aktiver Login → prüfen, ob Login vergessen wurde
    # ==========================================================
    has_in_today = False
    for ts in timestamps:
        if ts.get("type") == "in" and ts.get("time", "").startswith(today_str):
            has_in_today = True
            break

    if not has_in_today and now_dt.hour >= DEFAULT_LATE_LOGIN:
        # Login am Morgen vergessen → Auto-Login um DEFAULT_WORK_START + Auto-Logout jetzt
        auto_in = now_dt.replace(
            hour=DEFAULT_WORK_START[0],
            minute=DEFAULT_WORK_START[1],
            second=0,
        )
        auto_in_str = auto_in.strftime("%Y-%m-%d %H:%M:%S")

        timestamps.append({
            "time": auto_in_str,
            "type": "in",
            "auto": True,
        })

        timestamps.append({
            "time": now_str,
            "type": "out",
            "auto": True,
        })

        save_timestamps(timestamps_path, timestamps)
        set_pending_corrections_flag(True)

        message = (
            f"Nutzer {user_id} ({user_data['first_name']} "
            f"{user_data['last_name']}) hat den Login am Morgen vergessen. "
            f"Automatischer Login um {auto_in.strftime('%H:%M')} und "
            f"Logout um {now_dt.strftime('%H:%M')} gesetzt."
        )
        return message

    # ==========================================================
    # Fall C: Normaler Login
    # ==========================================================
    timestamps.append({
        "time": now_str,
        "type": "in",
        "auto": False,
    })
    save_timestamps(timestamps_path, timestamps)

    message = (
        f"Nutzer {user_id} ({user_data['first_name']} "
        f"{user_data['last_name']}) hat sich angemeldet um {now_dt.strftime('%H:%M')}."
    )
    return message



# ==========================================================
# ZEITERFASSUNG PER NFC-KARTE
# ==========================================================
def clock_with_nfc(nfc_code: str) -> str:
    """
    Führt An-/Abmeldung anhand eines NFC-Codes aus.
    Wird vom NFC-Listener aufgerufen.
    """
    userlist = load_userlist()

    for user_id, data in userlist.items():
        if data.get("nfc_code") == nfc_code:
            return clock(user_id)

    return f"Unbekannter NFC-Code: {nfc_code}"


# ==========================================================
# OFFENE AUTOMATISCHE KORREKTUREN ERMITTELN
# ==========================================================
def get_pending_corrections_for_user(user_id: str) -> list[dict]:
    """
    Liefert automatisch gesetzte Einträge (Auto-Login / Auto-Logout)
    für einen bestimmten Nutzer, die potenziell korrigiert werden können.

    Bereits akzeptierte Einträge (auto_confirmed=True) werden ignoriert.
    """
    userlist = load_userlist()
    user = userlist.get(user_id)
    if not user:
        return []

    path = os.path.join(user["folder"], f"{user['folder']}_timestamps.txt")
    ts = load_timestamps(path)
    results: list[dict] = []

    for entry in ts:
        # Bereits akzeptierte Auto-Einträge überspringen
        if entry.get("auto_confirmed"):
            continue

        try:
            dt = datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")
        except (KeyError, ValueError):
            # Ungültige Zeitangaben ignorieren
            continue

        hhmmss = dt.strftime("%H:%M:%S")

        # Prüfen auf automatisch gesetzte Standardzeiten (09:00 bzw. 18:00)
        is_auto_in = (
            entry.get("type") == "in"
            and hhmmss == f"{DEFAULT_WORK_START[0]:02d}:{DEFAULT_WORK_START[1]:02d}:{DEFAULT_WORK_START[2]:02d}"
        )
        is_auto_out = (
            entry.get("type") == "out"
            and hhmmss == f"{DEFAULT_WORK_END[0]:02d}:{DEFAULT_WORK_END[1]:02d}:{DEFAULT_WORK_END[2]:02d}"
        )

        if is_auto_in or is_auto_out:
            results.append(
                {
                    "type": entry["type"],
                    "date": dt.strftime("%Y-%m-%d"),
                }
            )

    return results


# ==========================================================
# MANUELLER TESTSTARTPUNKT
# ==========================================================
if __name__ == "__main__":
    # Einfacher Testaufruf für die Konsole
    print("Test: get_pending_corrections_for_user('1')")
    print(get_pending_corrections_for_user("1"))
