# nfc_listener.py

import nfc
import json
import os
from datetime import datetime
from timeclock import clock_with_nfc

UNKNOWN_CARDS_FILE = "unknown_cards.json"
PENDING_FILE = "pending_nfc.json"


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


def save_pending_card(nfc_code: str):
    """Speichert den zuletzt eingelesenen NFC-Code in pending_nfc.json."""
    entry = {
        "nfc_code": nfc_code,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=4, ensure_ascii=False)
    print(f"💾 Letzte Karte gespeichert ({nfc_code}) → pending_nfc.json")


def on_connect(tag):
    """Wird aufgerufen, wenn eine NFC-Karte erkannt wird."""
    nfc_id = tag.identifier.hex().upper()
    print(f"\n📶 Karte erkannt: {nfc_id}")

    # Letzten NFC-Code immer speichern (für Admin-Zuordnung)
    save_pending_card(nfc_id)

    # Danach normale Verarbeitung
    result = clock_with_nfc(nfc_id)

    if "Unbekannter NFC-Code" in result:
        save_unknown_card(nfc_id)

    print(result)
    print("-" * 50)
    return False  # nur einmal pro Karte reagieren


def run_nfc_listener():
    """Startet den NFC-Reader und wartet auf Karten."""
    try:
        clf = nfc.ContactlessFrontend('usb')
        print("✅ NFC-Reader gestartet – bitte Karte vorhalten...\n")
        while True:
            clf.connect(rdwr={'on-connect': on_connect})
    except Exception as e:
        print(f"❌ Fehler beim Starten des NFC-Readers: {e}")


if __name__ == "__main__":
    run_nfc_listener()
