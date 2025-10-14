import os
from datetime import datetime
from zfa_utils import (
    load_userlist,
    load_timestamps,
    save_timestamps,
    seconds_to_hours_minutes_str,
    set_pending_corrections_flag,
)

# ==========================================================
# KONSTANTEN – Standard-Arbeitszeiten
# ==========================================================
DEFAULT_WORK_START = (9, 0, 0)   # 09:00 Uhr
DEFAULT_WORK_END   = (18, 0, 0)  # 18:00 Uhr
DEFAULT_LATE_LOGIN = 15          # 15:00 Uhr

"""
  Setzt die Standartsarbeitszeit auf 9-18 Uhr und setzt 15 Uhr als Grenzzeit für einen Vergessen Login am Morgen
  """


# ==========================================================
# FUNKTION: Fehlerprotokoll
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
# FUNKTION: Zeitbuchung (Login / Logout)
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

    # Fall A: Letzter Eintrag war "in" → normaler oder vergessener Logout
    if timestamps and timestamps[-1]["type"] == "in":
        last_in = datetime.strptime(timestamps[-1]["time"], "%Y-%m-%d %H:%M:%S")

        if last_in.date() < now_dt.date():
            # Vergessenes Logout am Vortag → automatischer Logout 18:00
            auto_out = last_in.replace(hour=DEFAULT_WORK_END[0],
                                       minute=DEFAULT_WORK_END[1],
                                       second=DEFAULT_WORK_END[2])
            timestamps.append({"type": "out", "time": auto_out.strftime("%Y-%m-%d %H:%M:%S")})

            log_error(
                user_id,
                f"{user_data['first_name']} {user_data['last_name']}",
                f"Logout am {last_in.date()} vergessen → Auto-Logout {DEFAULT_WORK_END[0]:02d}:{DEFAULT_WORK_END[1]:02d} gesetzt"
            )

            set_pending_corrections_flag(True)  # ⚠️ Korrektur-Flag setzen

            action = "in"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} {user_data['last_name']}) "
                f"hat den Vortag nicht abgemeldet. Automatische Abmeldung um "
                f"{auto_out.strftime('%H:%M')} gesetzt. Neuer Arbeitstag gestartet (angemeldet)."
            )
        else:
            # Normales Logout
            duration = now_dt - last_in
            duration_str = seconds_to_hours_minutes_str(duration.total_seconds())
            action = "out"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} {user_data['last_name']}) "
                f"hat sich abgemeldet. Sitzungslänge: {duration_str}."
            )

    # Fall B: Kein aktiver Login → prüfen, ob Login vergessen wurde
    else:
        today_str = now_dt.strftime("%Y-%m-%d")
        has_in_today = any(
            ts["type"] == "in" and ts["time"].startswith(today_str)
            for ts in timestamps
        )

        if not has_in_today and now_dt.hour >= DEFAULT_LATE_LOGIN :
            # Login am Morgen vergessen → Auto-Login 09:00 + aktueller Logout
            auto_in = now_dt.replace(hour=DEFAULT_WORK_START[0],
                                     minute=DEFAULT_WORK_START[1],
                                     second=DEFAULT_WORK_START[2])
            timestamps.append({"type": "in", "time": auto_in.strftime("%Y-%m-%d %H:%M:%S")})

            log_error(
                user_id,
                f"{user_data['first_name']} {user_data['last_name']}",
                f"Login am Morgen vergessen → Auto-Login {DEFAULT_WORK_START[0]:02d}:{DEFAULT_WORK_START[1]:02d} gesetzt, sofortiges Logout"
            )

            set_pending_corrections_flag(True)  # ⚠️ Korrektur-Flag setzen

            action = "out"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} {user_data['last_name']}) "
                f"hat vergessen, sich morgens anzumelden. "
                f"Automatisches Login um {auto_in.strftime('%H:%M')} gesetzt. Jetzt abgemeldet."
            )
        else:
            # Normales Login
            action = "in"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} {user_data['last_name']}) "
                f"hat sich angemeldet."
            )

    # Zeitstempel speichern
    timestamps.append({"type": action, "time": now_dt.strftime("%Y-%m-%d %H:%M:%S")})
    save_timestamps(timestamps_path, timestamps)

    return message


# ==========================================================
# FUNKTION: Zeiterfassung per NFC-Karte
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
# FUNKTION: Offene automatische Korrekturen ermitteln
# ==========================================================
def get_pending_corrections_for_user(user_id: str) -> list[dict]:
    """
    Liefert automatisch gesetzte Einträge (Auto-Login / Auto-Logout)
    für einen bestimmten Nutzer, die potenziell korrigiert werden können.

    Rückgabeformat:
    [
        {"type": "in", "date": "2025-10-13"},
        {"type": "out", "date": "2025-10-14"}
    ]
    """
    userlist = load_userlist()
    user = userlist.get(user_id)
    if not user:
        return []

    path = os.path.join(user["folder"], f"{user['folder']}_timestamps.txt")
    ts = load_timestamps(path)
    results = []

    for entry in ts:
        try:
            dt = datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")
        except (KeyError, ValueError):
            continue  # Ungültige Zeit ignorieren

        hhmmss = dt.strftime("%H:%M:%S")

        # Prüfen auf automatisch gesetzte Standardzeiten
        if (
            (entry["type"] == "in" and hhmmss == f"{DEFAULT_WORK_START[0]:02d}:{DEFAULT_WORK_START[1]:02d}:{DEFAULT_WORK_START[2]:02d}")
            or (entry["type"] == "out" and hhmmss == f"{DEFAULT_WORK_END[0]:02d}:{DEFAULT_WORK_END[1]:02d}:{DEFAULT_WORK_END[2]:02d}")
        ):
            results.append({"type": entry["type"], "date": dt.strftime("%Y-%m-%d")})

    return results


# ==========================================================
# STARTPUNKT (nur für manuelle Tests)
# ==========================================================
if __name__ == "__main__":
    print("Test: get_pending_corrections_for_user('1')")
    print(get_pending_corrections_for_user("1"))
