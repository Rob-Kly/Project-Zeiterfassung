import os
import json

# ==========================================================
# Basisfunktionen für Benutzer- und Zeitdaten
# ==========================================================
def load_userlist() -> dict:
    """Lädt die userlist.txt und gibt sie als Dictionary zurück."""
    if not os.path.exists("userlist.txt"):
        return {}
    with open("userlist.txt", "r", encoding="utf-8") as f:
        return json.load(f)


def save_userlist(userlist: dict) -> None:
    """Speichert die userlist.txt."""
    with open("userlist.txt", "w", encoding="utf-8") as f:
        json.dump(userlist, f, indent=4, ensure_ascii=False)


def load_timestamps(path: str) -> list:
    """Lädt eine Timestamp-Datei eines Nutzers (falls vorhanden)."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_timestamps(path: str, timestamps: list) -> None:
    """Speichert eine Timestamp-Datei eines Nutzers."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(timestamps, f, indent=4, ensure_ascii=False)


def seconds_to_hours_minutes_str(seconds: float) -> str:
    """Wandelt Sekunden in Stunden und Minuten um und gibt String zurück."""
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"


# ==========================================================
# Flag-System für automatische Korrekturen
# ==========================================================
PENDING_CORRECTIONS_FILE = "pending_corrections.json"


def set_pending_corrections_flag(state: bool):
    """Setzt das Flag, ob neue automatische Buchungen vorhanden sind."""
    with open(PENDING_CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump({"new_pending_corrections": state}, f, indent=4, ensure_ascii=False)


def get_pending_corrections_flag() -> bool:
    """Liest das Flag, ob neue automatische Buchungen vorhanden sind."""
    if not os.path.exists(PENDING_CORRECTIONS_FILE):
        return False
    try:
        with open(PENDING_CORRECTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("new_pending_corrections", False)
    except json.JSONDecodeError:
        return False
