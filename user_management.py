import os
from zfa_utils import load_userlist, save_userlist


def add_user(user_id: str, first_name: str, last_name: str, nfc_code: str = None) -> str:
    """Fügt einen neuen Nutzer hinzu und legt seinen Ordner an."""
    userlist = load_userlist()

    if user_id in userlist:
        return f"User-ID {user_id} existiert bereits."

    folder = f"user_{user_id}"
    os.makedirs(folder, exist_ok=True)

    userlist[user_id] = {
        "first_name": first_name,
        "last_name": last_name,
        "nfc_code": nfc_code,
        "folder": folder
    }
    save_userlist(userlist)

    return f"Nutzer {first_name} {last_name} mit ID {user_id} wurde angelegt."


def update_user(user_id: str, first_name: str = None, last_name: str = None, nfc_code: str = None) -> str:
    """Aktualisiert die Daten eines bestehenden Nutzers."""
    userlist = load_userlist()

    if user_id not in userlist:
        return f"Unbekannte User-ID {user_id}"

    if first_name:
        userlist[user_id]["first_name"] = first_name
    if last_name:
        userlist[user_id]["last_name"] = last_name
    if nfc_code:
        userlist[user_id]["nfc_code"] = nfc_code

    save_userlist(userlist)
    return f"Nutzerdaten für ID {user_id} wurden aktualisiert."


def update_nfc_code(user_id: str, nfc_code: str) -> str:
    """Aktualisiert nur den NFC-Code eines Nutzers."""
    return update_user(user_id, nfc_code=nfc_code)


def remove_user(user_id: str) -> str:
    """Entfernt einen Nutzer aus der userlist (Ordner bleibt erhalten)."""
    userlist = load_userlist()

    if user_id not in userlist:
        return f"Unbekannte User-ID {user_id}"

    del userlist[user_id]
    save_userlist(userlist)

    return f"Nutzer mit ID {user_id} wurde aus der Liste entfernt (Ordner bleibt bestehen)."
