import os
from datetime import datetime
from zfa_utils import load_userlist, load_timestamps, save_timestamps, seconds_to_hours_minutes_str

# Standard-Arbeitszeiten
DEFAULT_WORK_START = (9, 0, 0)   # 09:00 Uhr
DEFAULT_WORK_END   = (18, 0, 0)  # 18:00 Uhr


def log_error(user_id: str, user_name: str, message: str) -> None:
    """Schreibt einen Fehlerfall in error_log.txt."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{now} | User {user_id} ({user_name}) | Fehler: {message}\n"
    with open("error_log.txt", "a", encoding="utf-8") as f:
        f.write(entry)


def clock(user_id: str) -> str:
    """Registriert einen Login/Logout für einen Nutzer und behandelt Fehlerfälle."""

    userlist = load_userlist()
    if user_id not in userlist:
        return f"Unbekannte User-ID {user_id}"

    user_data = userlist[user_id]
    user_folder = user_data["folder"]
    timestamps_path = os.path.join(user_folder, f"{user_folder}_timestamps.txt")

    timestamps = load_timestamps(timestamps_path)
    now_dt = datetime.now()

    # Fall A: Letzter Eintrag war "in"
    if timestamps and timestamps[-1]["type"] == "in":
        last_in = datetime.strptime(timestamps[-1]["time"], "%Y-%m-%d %H:%M:%S")

        if last_in.date() < now_dt.date():
            # Vergessenes Logout am Vortag → Auto-Logout 18:00
            auto_out = last_in.replace(hour=DEFAULT_WORK_END[0],
                                       minute=DEFAULT_WORK_END[1],
                                       second=DEFAULT_WORK_END[2])
            timestamps.append({"type": "out", "time": auto_out.strftime("%Y-%m-%d %H:%M:%S")})

            log_error(user_id, f"{user_data['first_name']} {user_data['last_name']}",
                      f"Logout am {last_in.date()} vergessen → Auto-Logout {DEFAULT_WORK_END[0]:02d}:{DEFAULT_WORK_END[1]:02d} gesetzt")

            action = "in"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} {user_data['last_name']}) "
                f"hat den Vortag nicht abgemeldet. Automatische Abmeldung um {auto_out.strftime('%H:%M')} gesetzt. "
                f"Neuer Arbeitstag gestartet (angemeldet)."
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

    else:
        # Fall B: Prüfen ob vergessenes Login
        today_str = now_dt.strftime("%Y-%m-%d")
        has_in_today = any(
            ts["type"] == "in" and ts["time"].startswith(today_str)
            for ts in timestamps
        )

        if not has_in_today and now_dt.hour >= 15:
            # Login am Morgen vergessen → Auto-Login um 09:00 + aktuelles Logout
            auto_in = now_dt.replace(hour=DEFAULT_WORK_START[0],
                                     minute=DEFAULT_WORK_START[1],
                                     second=DEFAULT_WORK_START[2])
            timestamps.append({"type": "in", "time": auto_in.strftime("%Y-%m-%d %H:%M:%S")})

            action = "out"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} {user_data['last_name']}) "
                f"hat vergessen sich morgens anzumelden. "
                f"Automatisches Login um {auto_in.strftime('%H:%M')} gesetzt. Jetzt abgemeldet."
            )

            log_error(user_id, f"{user_data['first_name']} {user_data['last_name']}",
                      f"Login am Morgen vergessen → Auto-Login {DEFAULT_WORK_START[0]:02d}:{DEFAULT_WORK_START[1]:02d} gesetzt, sofortiges Logout")

        else:
            # Normales Login
            action = "in"
            message = (
                f"Nutzer {user_id} ({user_data['first_name']} {user_data['last_name']}) "
                f"hat sich angemeldet."
            )

    # Speichern
    timestamps.append({"type": action, "time": now_dt.strftime("%Y-%m-%d %H:%M:%S")})
    save_timestamps(timestamps_path, timestamps)

    return message


def clock_with_nfc(nfc_code: str) -> str:
    """Führt Login/Logout anhand eines NFC-Codes aus."""
    userlist = load_userlist()

    for user_id, data in userlist.items():
        if data.get("nfc_code") == nfc_code:
            return clock(user_id)

    return f"Unbekannter NFC-Code: {nfc_code}"
