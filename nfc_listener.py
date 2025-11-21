# nfc_listener.py

import time
import nfc
import json
import os
from datetime import datetime
from attendance import clock_with_nfc
from config import DEBOUNCE_SECONDS


PENDING_FILE = "pending_nfc.json"

# Globale Variablen für Entprellung / Debounce
LAST_NFC_CODE = None
LAST_NFC_TIME = 0.0


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
    global LAST_NFC_CODE, LAST_NFC_TIME

    nfc_id = tag.identifier.hex().upper()
    now = time.time()

    # Entprellung: gleiche Karte innerhalb von 2 Sekunden ignorieren
    if nfc_id == LAST_NFC_CODE and (now - LAST_NFC_TIME) < DEBOUNCE_SECONDS:
        return False

    LAST_NFC_CODE = nfc_id
    LAST_NFC_TIME = now

    print(f"\n📶 Karte erkannt: {nfc_id}")

    # Letzten NFC-Code immer speichern (für Admin-Zuordnung)
    save_pending_card(nfc_id)

    # Danach normale Verarbeitung
    result = clock_with_nfc(nfc_id)

    print(result)
    print("-" * 50)
    return False


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
