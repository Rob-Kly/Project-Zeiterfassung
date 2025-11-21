import os
import json

"""
Flag-System für automatisch gesetzte Buchungen
(z.B. Auto-Login/Auto-Logout), damit der Admin
im Webinterface eine Warnung angezeigt bekommt.
"""

# ==========================================================
# KONFIGURATION
# ==========================================================
PENDING_CORRECTIONS_FILE = "pending_corrections.json"


# ==========================================================
# FLAG-VERWALTUNG
# ==========================================================
def set_pending_corrections_flag(state: bool) -> None:
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
