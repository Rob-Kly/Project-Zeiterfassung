import os
from datetime import datetime

from zfa_io import load_userlist, save_userlist

"""
Verwaltung der Benutzerdaten (userlist.txt).

Aufgaben:
- Anlegen neuer Benutzer (inkl. automatischer ID und Ordner)
- Aktualisieren bestehender Benutzer
- Entfernen von Benutzern aus der userlist
- Suchen eines Benutzers anhand des NFC-Codes
"""


# ==========================================================
# INTERN: NÄCHSTE FREIE USER-ID ERMITTELN
# ==========================================================
def _next_free_id(userlist: dict) -> str:
    """
    Ermittelt die nächste freie numerische User-ID als String.

    Beispiel:
        userlist enthält IDs "1", "2", "5" → Rückgabe: "6"
        ist die Liste leer → Rückgabe: "1"
    """
    if not userlist:
        return "1"

    existing = [int(uid) for uid in userlist.keys() if uid.isdigit()]
    return str(max(existing) + 1 if existing else 1)


# ==========================================================
# BENUTZER ANLEGEN
# ==========================================================
def add_user(first_name: str,
             last_name: str,
             nfc_code: str | None = None,
             password: str | None = None,
             role: str = "user") -> str:
    """
    Fügt einen neuen Nutzer zur userlist hinzu, vergibt automatisch die nächste freie ID
    und legt den Benutzerordner an.

    :param first_name: Vorname
    :param last_name: Nachname
    :param nfc_code: Optionaler NFC-Code
    :param password: Optionales Startpasswort
    :param role: "user" oder "admin"
    :return: Statusnachricht als String
    """
    userlist = load_userlist()

    new_id = _next_free_id(userlist)
    folder = f"user_{new_id}_{first_name}_{last_name}"
    os.makedirs(folder, exist_ok=True)

    now_str = datetime.now().isoformat(timespec="seconds")

    userlist[new_id] = {
        "first_name": first_name,
        "last_name": last_name,
        "nfc_code": nfc_code,
        "folder": folder,
        "password": password or "",
        "role": role,
        # Wenn ein Passwort gesetzt wird, soll der Nutzer es beim ersten Login ändern:
        "password_must_change": bool(password),
        "password_set_at": now_str if password else None,
    }
    save_userlist(userlist)

    return f"Nutzer {first_name} {last_name} mit ID {new_id} wurde angelegt."


# ==========================================================
# BENUTZERDATEN AKTUALISIEREN
# ==========================================================
def update_user(user_id: str,
                first_name: str | None = None,
                last_name: str | None = None,
                nfc_code: str | None = None,
                password: str | None = None,
                role: str | None = None) -> str:
    """
    Aktualisiert Felder eines bestehenden Nutzers. Nur übergebene Parameter werden geändert.

    :param user_id: ID des Nutzers
    :param first_name: Neuer Vorname oder None (keine Änderung)
    :param last_name: Neuer Nachname oder None (keine Änderung)
    :param nfc_code: Neuer NFC-Code oder None (keine Änderung)
    :param password: Neues Passwort oder None/"" (keine Änderung)
    :param role: Neue Rolle ("user"/"admin") oder None (keine Änderung)
    :return: Statusnachricht
    """
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
        userlist[user_id]["password_must_change"] = True
        userlist[user_id]["password_set_at"] = datetime.now().isoformat(timespec="seconds")

    if role is not None:
        userlist[user_id]["role"] = role

    save_userlist(userlist)
    return f"Nutzerdaten für ID {user_id} wurden aktualisiert."


# ==========================================================
# NUR NFC-CODE AKTUALISIEREN
# ==========================================================
def update_nfc_code(user_id: str, nfc_code: str) -> str:
    """
    Aktualisiert ausschließlich den NFC-Code eines Nutzers.

    Diese Funktion ist ein Convenience-Wrapper um update_user().
    """
    return update_user(user_id, nfc_code=nfc_code)


# ==========================================================
# BENUTZER ENTFERNEN
# ==========================================================
def remove_user(user_id: str) -> str:
    """
    Entfernt einen Nutzer aus der userlist.

    Der zugehörige Ordner auf dem Dateisystem bleibt unverändert bestehen.
    """
    userlist = load_userlist()
    if user_id not in userlist:
        return f"Unbekannte User-ID {user_id}"

    del userlist[user_id]
    save_userlist(userlist)
    return f"Nutzer mit ID {user_id} wurde aus der Liste entfernt (Ordner bleibt bestehen)."


# ==========================================================
# NUTZER PER NFC-CODE SUCHEN
# ==========================================================
def find_user_by_nfc(nfc_code: str, exclude_user_id: str | None = None):
    """
    Sucht in der userlist nach einem Nutzer mit dem angegebenen NFC-Code.

    :param nfc_code: NFC-Code, nach dem gesucht werden soll
    :param exclude_user_id: Optionale User-ID, die bei der Suche ignoriert werden soll
                            (z.B. beim Bearbeiten des eigenen Datensatzes)
    :return: Tuple (user_id, user_dict) oder (None, None), falls nichts gefunden wurde.
    """
    if not nfc_code:
        return None, None

    userlist = load_userlist()
    for uid, data in userlist.items():
        if exclude_user_id is not None and uid == exclude_user_id:
            continue
        if data.get("nfc_code") == nfc_code:
            return uid, data

    return None, None
