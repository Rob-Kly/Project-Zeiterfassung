import os
import json

# Datei, in der alle Nutzer zentral gespeichert sind
USERLIST_PATH = "userlist.json"


def load_userlist() -> dict:
    """Lädt die zentrale Nutzerliste. Falls sie nicht existiert, wird ein leeres Dict zurückgegeben."""
    if not os.path.exists(USERLIST_PATH):
        return {}
    with open(USERLIST_PATH, "r", encoding="utf-8") as userlist_file:
        return json.load(userlist_file)


def save_userlist(userlist: dict) -> None:
    """Speichert die komplette Nutzerliste zurück in die zentrale Datei."""
    with open(USERLIST_PATH, "w", encoding="utf-8") as userlist_file:
        json.dump(userlist, userlist_file, indent=4, ensure_ascii=False)


def create_user(first_name: str, last_name: str, birthday: str = "") -> None:
    """Legt einen neuen Nutzerordner und die dazugehörigen Dateien an und ergänzt ihn in der Nutzerliste."""

    # Nutzerliste laden
    userlist = load_userlist()

    # Neue eindeutige ID erzeugen
    new_id = (str(len(userlist) + 1)).zfill(3)

    # Ordnername: First_Last
    user_folder = f"{first_name}_{last_name}"
    os.makedirs(user_folder, exist_ok=True)

    # Pfad für Stammdaten-Datei
    info_path = os.path.join(user_folder, f"{user_folder}_info.txt")

    # Stammdaten schreiben
    with open(info_path, "w", encoding="utf-8") as info_file:
        info_file.write(f"ID: {new_id}\n")
        info_file.write(f"First name: {first_name}\n")
        info_file.write(f"Last name: {last_name}\n")
        if birthday:
            info_file.write(f"Birthday: {birthday}\n")

    # Pfad für Zeitstempel-Datei (noch leer, nur angelegt)
    timestamps_path = os.path.join(user_folder, f"{user_folder}_timestamps.txt")
    open(timestamps_path, "a", encoding="utf-8").close()

    # Nutzer in die zentrale Liste eintragen
    userlist[new_id] = {
        "first_name": first_name,
        "last_name": last_name,
        "folder": user_folder,
        "birthday": birthday,
    }

    # Nutzerliste speichern
    save_userlist(userlist)
