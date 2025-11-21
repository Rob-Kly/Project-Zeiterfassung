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
def clock(user_id: str) -> str:
    """
    Registriert eine An- oder Abmeldung für einen Benutzer.

    Behandelt automatisch Fehlerfälle (vergessene Logins/Logouts)
    und setzt ggf. ein Flag für neue automatische Korrekturen.
    """
    userlist = load_userlist()
    if user_id not in userlist:
        return f"Unbekannte User-ID {user_id}"

    user_data = userlist[user_id]
    user_folder = user_data["folder"]
    timestamps_path = os.path.join(user_folder, f"{user_folder}_timestamps.txt")

    timestamps = load_timestamps(timestamps_path)
    now_dt = datetime.now()

    # ----------------------------------------------------------
    # Fall A: Letzter Eintrag war "in" → normaler oder vergessener Logout
    # ----------------------------------------------------------
    if timestamps and timestamps[-1]["type"] == "in":
        last_in = datetime.strptime(timestamps[-1]["time"], "%Y-%m-%d %H:%M:%S")

        if last_in.date() < now_dt.date():
            # Vergessenes Logout am Vortag → automatischer Logout um DEFAULT_WORK_END
            auto_out = last_in.replace(
                hour=DEFAULT_WORK_END[0],
                minute=DEFAULT_WORK_END[1],
                second=DEFAULT_WORK_END[2],
            )
            timestamps.append(
                {"type": "out", "time": auto_out.strftime("%Y-%m-%d %H:%M:%S")}
            )

            log_error(
                user_id,
                f"{user_data['first_name']} {user_data['last_name']}",
                (
                    "Logout am {date} vergessen → Auto-Logout "
                    "{end_h:02d}:{end_m:02d} gesetzt"
                ).format(
                    date=last_in.date(),
                    end_h=DEFAULT_WORK_END[0],
                    end_m=DEFAULT_WORK_END[1],
                ),
            )

            # Flag für neue automatische Korrekturen setzen
            set_pending_corrections_flag(True)

            action = "in"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} "
                f"{user_data['last_name']}) hat den Vortag nicht abgemeldet. "
                f"Automatische Abmeldung um {auto_out.strftime('%H:%M')} gesetzt. "
                "Neuer Arbeitstag gestartet (angemeldet)."
            )
        else:
            # Normales Logout
            duration = now_dt - last_in
            duration_str = seconds_to_hours_minutes_str(duration.total_seconds())
            action = "out"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} "
                f"{user_data['last_name']}) hat sich abgemeldet. "
                f"Sitzungslänge: {duration_str}."
            )

    # ----------------------------------------------------------
    # Fall B: Kein aktiver Login → prüfen, ob Login vergessen wurde
    # ----------------------------------------------------------
    else:
        today_str = now_dt.strftime("%Y-%m-%d")
        has_in_today = any(
            ts["type"] == "in" and ts["time"].startswith(today_str)
            for ts in timestamps
        )

        if not has_in_today and now_dt.hour >= DEFAULT_LATE_LOGIN:
            # Login am Morgen vergessen → Auto-Login um DEFAULT_WORK_START + aktueller Logout
            auto_in = now_dt.replace(
                hour=DEFAULT_WORK_START[0],
                minute=DEFAULT_WORK_START[1],
                second=DEFAULT_WORK_START[2],
            )
            timestamps.append(
                {"type": "in", "time": auto_in.strftime("%Y-%m-%d %H:%M:%S")}
            )

            log_error(
                user_id,
                f"{user_data['first_name']} {user_data['last_name']}",
                (
                    "Login am Morgen vergessen → Auto-Login "
                    "{start_h:02d}:{start_m:02d} gesetzt, sofortiges Logout"
                ).format(
                    start_h=DEFAULT_WORK_START[0],
                    start_m=DEFAULT_WORK_START[1],
                ),
            )

            # Flag für neue automatische Korrekturen setzen
            set_pending_corrections_flag(True)

            action = "out"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} "
                f"{user_data['last_name']}) hat vergessen, sich morgens anzumelden. "
                f"Automatisches Login um {auto_in.strftime('%H:%M')} gesetzt. "
                "Jetzt abgemeldet."
            )
        else:
            # Normales Login
            action = "in"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} "
                f"{user_data['last_name']}) hat sich angemeldet."
            )

    # ----------------------------------------------------------
    # Zeitstempel speichern
    # ----------------------------------------------------------
    timestamps.append({"type": action, "time": now_dt.strftime("%Y-%m-%d %H:%M:%S")})
    save_timestamps(timestamps_path, timestamps)

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
