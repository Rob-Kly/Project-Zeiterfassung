# nfc_listener.py (libnfc-Version für ACR122U)

import json
import os
import subprocess
import time
from datetime import datetime
from timeclock import clock_with_nfc

UNKNOWN_CARDS_FILE = "unknown_cards.json"


def save_unknown_card(nfc_code: str):
    """Speichert unbekannte NFC-Codes mit Zeitstempel als JSON-Liste."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": now,
        "nfc_code": nfc_code,
        "status": "unassigned"
    }

    data = []
    if os.path.exists(UNKNOWN_CARDS_FILE):
        try:
            with open(UNKNOWN_CARDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []

    data.append(entry)

    with open(UNKNOWN_CARDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_nfc_uid():
    """Liest den NFC-UID mit libnfc (nfc-list) aus."""
    try:
        result = subprocess.run(["nfc-list"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "UID" in line:
                return line.split(":")[1].strip().replace(" ", "").upper()
    except Exception as e:
        print(f"❌ Fehler beim Lesen der NFC-Karte: {e}")
    return None


def run_nfc_listener():
    """Startet die NFC-Abfrage über libnfc."""
    print("✅ NFC-Listener (libnfc) gestartet – bitte Karte vorhalten...\n")
    try:
        last_uid = None
        while True:
            uid = get_nfc_uid()
            if uid and uid != last_uid:
                print(f"\n📶 Karte erkannt: {uid}")
                result = clock_with_nfc(uid)
                if "Unbekannter NFC-Code" in result:
                    save_unknown_card(uid)
                print(result)
                print("-" * 50)
                last_uid = uid
            time.sleep(1)  # kleine Pause, um CPU zu schonen
    except KeyboardInterrupt:
        print("\n🛑 Beendet durch Benutzer.")


if __name__ == "__main__":
    run_nfc_listener()
