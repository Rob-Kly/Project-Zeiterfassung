# nfc_listener.py

import nfc
import json
import os
import requests
from datetime import datetime

# Adresse deines lokalen Webservers
API_URL = "http://localhost:8080/api/clock"

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


def send_to_api(user_id: str):
    """Sendet den Clock-Vorgang an den Webserver."""
    try:
        response = requests.post(API_URL, json={"user_id": user_id}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Serverantwort: {data.get('message', 'OK')}")
        else:
            print(f"❌ Fehler vom Server: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Keine Verbindung zum Server: {e}")


def on_connect(tag):
    """Wird aufgerufen, wenn eine NFC-Karte erkannt wird."""
    nfc_id = tag.identifier.hex().upper()
    print(f"\n📶 Karte erkannt: {nfc_id}")

    # Versuche, die Karte über den Webserver zu verarbeiten
    send_to_api(nfc_id)

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
