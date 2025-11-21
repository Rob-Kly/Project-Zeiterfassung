import re

"""
Passwortregeln und Auswertung der Benutzer-Formulare
(Vorname/Nachname/NFC/Passwort/Rolle).
"""

# ==========================================================
# PASSWORT-REGELN
# ==========================================================
PASSWORD_REQUIREMENTS_TEXT = (
    "Passwort erfüllt nicht die Mindestanforderungen "
    "(mind. 8 Zeichen, Groß- und Kleinschreibung, Zahl/Sonderzeichen)."
)


def is_valid_password(pw: str) -> bool:
    """
    Prüft Passwort auf Mindestanforderungen:
    - mindestens 8 Zeichen
    - mindestens ein Großbuchstabe
    - mindestens ein Kleinbuchstabe
    - mindestens eine Ziffer ODER ein Sonderzeichen
    """
    if len(pw) < 8:
        return False
    if not re.search(r"[A-Z]", pw):        # Großbuchstabe
        return False
    if not re.search(r"[a-z]", pw):        # Kleinbuchstabe
        return False
    if not re.search(r"[0-9\W]", pw):      # Ziffer oder Sonderzeichen
        return False
    return True


# ==========================================================
# VALIDIERUNG PASSWORT-PAAR
# ==========================================================
def validate_password_pair(password: str, password2: str, required: bool):
    """
    Prüft ein Passwort-Paar aus Formularfeldern.

    :param password: erstes Passwortfeld
    :param password2: zweites Passwortfeld (Wiederholung)
    :param required: True = Passwort muss gesetzt werden, False = optional
    :return: (ok: bool, error: str | None, final_password: str | None)

    final_password:
      - bei Erfolg und gesetztem Passwort -> das neue Passwort
      - bei Erfolg und optional + leer gelassen -> None (keine Änderung)
    """
    password = (password or "").strip()
    password2 = (password2 or "").strip()

    # Pflichtpasswort: beide Felder müssen gefüllt sein
    if required and (not password or not password2):
        return False, "Bitte Passwort in beiden Feldern eingeben.", None

    # Wenn optional und komplett leer gelassen -> ok, keine Änderung
    if not required and not password and not password2:
        return True, None, None

    # Wenn eines von beiden gefüllt ist, das andere nicht -> Fehler
    if (password and not password2) or (password2 and not password):
        return False, "Bitte beide Passwortfelder ausfüllen.", None

    # Felder vorhanden -> Gleichheit prüfen
    if password != password2:
        return False, "Die Passwörter stimmen nicht überein.", None

    # Inhaltliche Regeln prüfen
    if not is_valid_password(password):
        return False, PASSWORD_REQUIREMENTS_TEXT, None

    # Alles ok
    return True, None, password


# ==========================================================
# FORMULARAUSWERTUNG USER-FORM
# ==========================================================
def parse_user_form(form, password_required: bool):
    """
    Liest und prüft ein Benutzer-Formular (Vorname, Nachname, NFC, Passwort, Rolle).

    :param form: z.B. request.form
    :param password_required: True = Passwort Pflicht (Neuanlage), False = optional (Bearbeiten)
    :return: (ok: bool, error: str | None, data: dict | None)

    data enthält bei Erfolg:
        {
            "first_name": str,
            "last_name": str,
            "nfc_code": str | None,
            "password": str | None,
            "role": str
        }
    """
    first_name = (form.get("first_name") or "").strip()
    last_name = (form.get("last_name") or "").strip()
    nfc_code = (form.get("nfc_code") or "").strip() or None
    password = form.get("password", "")
    password2 = form.get("password2", "")
    role = (form.get("role") or "user").strip() or "user"

    if not first_name or not last_name:
        return False, "Bitte Vorname und Nachname ausfüllen.", None

    ok, pw_error, final_password = validate_password_pair(password, password2, password_required)
    if not ok:
        return False, pw_error, None

    data = {
        "first_name": first_name,
        "last_name": last_name,
        "nfc_code": nfc_code,
        "password": final_password,  # kann None sein (bei optionalem Passwort)
        "role": role,
    }
    return True, None, data
