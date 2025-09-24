import os
import time
import nfc
from datetime import datetime

USERS_FILE = "mitarbeiter.txt"
ATTENDANCE_FILE = "attendance.txt"


def ensure_files():
    """Erstellt die Dateien mit Kopfzeilen, falls sie noch nicht existieren."""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            f.write("UID;Name;Geburtsdatum;Startdatum\n")

    if not os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "w", encoding="utf-8") as f:
            f.write("UID;Datum;CheckIn;CheckOut;DauerMinuten\n")


def find_user(uid):
    """Sucht Benutzer anhand der UID in users.txt"""
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()[1:]  # Kopfzeile überspringen
        for line in lines:
            data = line.strip().split(";")
            if data[0] == uid:
                return {
                    "uid": data[0],
                    "name": data[1],
                    "geburtsdatum": data[2],
                    "startdatum": data[3],
                }
    return None


def add_user(uid):
    """Neuen Benutzer hinzufügen"""
    print("⚠ Neuer Benutzer erkannt. Bitte Daten eingeben:")
    name = input("Name: ")
    geburtsdatum = input("Geburtsdatum (YYYY-MM-DD): ")
    startdatum = input("Startdatum (YYYY-MM-DD): ")

    with open(USERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{uid};{name};{geburtsdatum};{startdatum}\n")

    print(f"✔ Benutzer {name} erfolgreich gespeichert.")


def record_attendance(uid):
    """Speichert Check-In oder Check-Out in attendance.txt"""
    now = datetime.now()
    datum = now.strftime("%Y-%m-%d")
    uhrzeit = now.strftime("%H:%M:%S")

    # Prüfen, ob heute schon ein Check-In existiert
    with open(ATTENDANCE_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines[1:], start=1):  # Kopfzeile überspringen
        data = line.strip().split(";")
        if data[0] == uid and data[1] == datum and data[3] == "":  # Check-Out fehlt
            checkin = datetime.strptime(data[2], "%H:%M:%S")
            dauer = int((now - checkin).total_seconds() // 60)  # Dauer in Minuten
            lines[i] = f"{uid};{datum};{data[2]};{uhrzeit};{dauer}\n"
            with open(ATTENDANCE_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines)
            print(f"✔ Check-Out gespeichert ({dauer} Minuten).")
            return

    # Falls kein offener Check-In: neuen Eintrag hinzufügen
    with open(ATTENDANCE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{uid};{datum};{uhrzeit};;\n")
    print("✔ Check-In gespeichert.")


def on_connect(tag):
    uid = tag.identifier.hex()
    print(f"\nKarte erkannt: UID = {uid}")

    user = find_user(uid)
    if not user:
        add_user(uid)  # Falls unbekannt: neuen Benutzer anlegen
    else:
        record_attendance(uid)

    return False  # wartet auf nächste Karte


if __name__ == "__main__":
    ensure_files()
    print("Bitte Karte auflegen... (Ctrl+C zum Beenden)")
    with nfc.ContactlessFrontend("usb") as clf:
        while True:
            clf.connect(rdwr={"on-connect": on_connect})
