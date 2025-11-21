import os
import json

"""
Basisfunktionen für Benutzer- und Zeitdaten:
- Laden/Speichern der userlist.txt
- Laden/Speichern von Timestamp-Dateien
- Umrechnung von Sekunden in Stunden/Minuten
"""

# ==========================================================
# USERLISTE LADEN / SPEICHERN
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


# ==========================================================
# TIMESTAMPS-LISTEN LADEN / SPEICHERN
# ==========================================================
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


# ==========================================================
# ZEIT-HILFSFUNKTIONEN
# ==========================================================
def seconds_to_hours_minutes_str(seconds: float) -> str:
    """
    Wandelt Sekunden in einen String 'Xh Ym' um.
    Beispiel: 3661 Sekunden → '1h 1m'
    """
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"
