# nfc_listener.py

import nfc
import json
import os
import subprocess
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


def on_connect(tag):
    """Wird aufgerufen, wenn eine NFC-Karte erkannt wird."""
    nfc_id = tag.identifier.hex().upper()
    print(f"\n📶 Karte erkannt: {nfc_id}")

    result = clock_with_nfc(nfc_id)

    if "Unbekannter NFC-Code" in result:
        save_unknown_card(nfc_id)

    print(result)
    print("-" * 50)
    return False  # nur einmal pro Karte reagieren


def fallback_libnfc():
    """Alternative Methode über libnfc, falls nfcpy den Reader nicht findet."""
    print("⚙️  Fallback: Verwende libnfc (nfc-list)...")
    try:
        while True:
            result = subprocess.run(["nfc-list"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "UID" in line:
                    uid = line.split(":")[1].strip().replace(" ", "").upper()
                    print(f"\n📶 Karte erkannt (libnfc): {uid}")
                    result_msg = clock_with_nfc(uid)
                    if "Unbekannter NFC-Code" in result_msg:
                        save_unknown_card(uid)
                    print(result_msg)
                    print("-" * 50)
            # kleine Pause, um CPU zu schonen
    except KeyboardInterrupt:
        print("\n🛑 Abbruch durch Benutzer.")
    except Exception as e:
        print(f"❌ Fehler im libnfc-Fallback: {e}")


def run_nfc_listener():
    """Startet den NFC-Reader und wartet auf Karten."""
    try:
        clf = nfc.ContactlessFrontend('usb')
        print("✅ NFC-Reader gestartet – bitte Karte vorhalten...\n")
        while True:
            clf.connect(rdwr={'on-connect': on_connect})
    except Exception as e:
        print(f"❌ Fehler beim Starten des NFC-Readers: {e}")
        fallback_libnfc()  # automatisch auf libnfc umschalten


if __name__ == "__main__":
    run_nfc_listener()
