import os
from zfa_utils import load_userlist, save_userlist

def _next_free_id(userlist: dict) -> str:
    if not userlist:
        return "1"
    existing = [int(uid) for uid in userlist.keys() if uid.isdigit()]
    return str(max(existing) + 1 if existing else 1)

def add_user(first_name: str, last_name: str,
             nfc_code: str = None, password: str = None, role: str = "user") -> str:
    """Fügt einen neuen Nutzer hinzu, vergibt automatisch die nächste freie ID und legt den Ordner an."""
    userlist = load_userlist()

    new_id = _next_free_id(userlist)
    folder = f"user_{new_id}"
    os.makedirs(folder, exist_ok=True)

    userlist[new_id] = {
        "first_name": first_name,
        "last_name": last_name,
        "nfc_code": nfc_code,
        "folder": folder,
        "password": password or "",
        "role": role
    }
    save_userlist(userlist)

    return f"Nutzer {first_name} {last_name} mit ID {new_id} wurde angelegt."

def update_user(user_id: str, first_name: str = None, last_name: str = None,
                nfc_code: str = None, password: str = None, role: str = None) -> str:
    """Aktualisiert Felder eines bestehenden Nutzers (nur übergebene Felder)."""
    userlist = load_userlist()
    if user_id not in userlist:
        return f"Unbekannte User-ID {user_id}"

    if first_name is not None:
        userlist[user_id]["first_name"] = first_name
    if last_name is not None:
        userlist[user_id]["last_name"] = last_name
    if nfc_code is not None:
        userlist[user_id]["nfc_code"] = nfc_code
    if password is not None and password != "":
        userlist[user_id]["password"] = password
    if role is not None:
        userlist[user_id]["role"] = role

    save_userlist(userlist)
    return f"Nutzerdaten für ID {user_id} wurden aktualisiert."

def update_nfc_code(user_id: str, nfc_code: str) -> str:
    """Aktualisiert nur den NFC-Code eines Nutzers."""
    return update_user(user_id, nfc_code=nfc_code)

def remove_user(user_id: str) -> str:
    """Entfernt einen Nutzer aus der userlist (Ordner bleibt bestehen)."""
    userlist = load_userlist()
    if user_id not in userlist:
        return f"Unbekannte User-ID {user_id}"
    del userlist[user_id]
    save_userlist(userlist)
    return f"Nutzer mit ID {user_id} wurde aus der Liste entfernt (Ordner bleibt bestehen)."
