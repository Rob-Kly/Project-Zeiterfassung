from datetime import datetime, timedelta

from flask import request, render_template, redirect, url_for, session

from zfa_io import load_userlist, save_userlist
from zfa_passwords import parse_user_form
from user_management import add_user
from config import PASSWORD_CHANGE_GRACE_HOURS

"""
Routen für Authentifizierung und Setup:

- /               → root_redirect
- /login          → login
- /change_password
- /logout
- /setup_admin
"""


def init_auth_routes(app):
    print("   → init_auth_routes() aufgerufen")

    # ==========================================================
    # ROOT → LOGIN
    # ==========================================================
    @app.route("/")
    def root_redirect():
        """Leitet die Hauptadresse direkt zur Login-Seite weiter."""
        return redirect(url_for("login"))

    # ==========================================================
    # LOGIN
    # ==========================================================
    @app.route("/login", methods=["GET", "POST"])
    def login():
        """
        Login-Seite für Benutzer und Administratoren.
        Benutzername = 'Vorname.Nachname', Passwort laut userlist.txt.
        """
        userlist = load_userlist()
        error = None

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""

            matched_user_id = None
            matched_user = None

            # Eingabe normalisieren: Leerzeichen entfernen, Kleinschreibung
            input_norm = username.lower().replace(" ", "")

            # Benutzer + Passwort suchen
            for user_id, user in userlist.items():
                first = (user.get("first_name") or "").strip().lower()
                last = (user.get("last_name") or "").strip().lower()

                # Erwartetes Loginformat: vorname.nachname
                expected_login = f"{first}.{last}"

                if input_norm == expected_login and user.get("password") == password:
                    matched_user_id = user_id
                    matched_user = user
                    break

            if not matched_user:
                error = "Falscher Benutzername oder Passwort!"
                return render_template("login.html", error=error)

            # Prüfen, ob Passwort als "muss geändert werden" markiert ist
            must_change = matched_user.get("password_must_change", False)

            if must_change:
                # Prüfen, ob 24h-Frist abgelaufen ist
                expired = False
                set_at_str = matched_user.get("password_set_at")
                if set_at_str:
                    try:
                        set_at = datetime.fromisoformat(set_at_str)
                        deadline = set_at + timedelta(hours=PASSWORD_CHANGE_GRACE_HOURS)
                        if datetime.now() > deadline:
                            expired = True
                    except ValueError:
                        # Falls der Zeitstempel kaputt ist, lieber blockieren
                        expired = True

                if expired:
                    return render_template(
                        "login.html",
                        error=(
                            "Das temporäre Passwort ist abgelaufen. "
                            "Bitte wende dich an einen Administrator."
                        ),
                    )

            # Session setzen
            full_name = f"{matched_user['first_name']} {matched_user['last_name']}"
            session["user_id"] = matched_user_id
            session["role"] = matched_user.get("role", "user")
            session["name"] = full_name
            session["last_activity"] = datetime.now().isoformat(timespec="seconds")

            # Wenn Passwort noch geändert werden muss → Zwangsweiterleitung
            if must_change:
                return redirect(url_for("change_password"))

            # Normale Weiterleitung nach Rolle
            if session["role"] == "admin":
                return redirect(url_for("admin_panel"))
            return redirect(url_for("user_home"))

        else:
            # GET-Request: ggf. Timeout-Hinweis anzeigen
            if request.args.get("reason") == "timeout":
                error = (
                    "Deine Sitzung ist nach 5 Minuten Inaktivität abgelaufen. "
                    "Bitte erneut anmelden."
                )

        return render_template("login.html", error=error)

    # ==========================================================
    # PASSWORT ÄNDERN
    # ==========================================================
    @app.route("/change_password", methods=["GET", "POST"])
    def change_password():
        """
        Erzwingt beim ersten Login mit einem vom Admin gesetzten Passwort,
        dass der Nutzer ein eigenes Passwort vergibt.
        """
        if "user_id" not in session:
            return redirect(url_for("login"))

        user_id = session["user_id"]
        userlist = load_userlist()
        user = userlist.get(user_id)

        if not user:
            # Falls der Nutzer aus der Liste gelöscht wurde
            session.clear()
            return redirect(url_for("login"))

        # Falls aus irgendeinem Grund kein Zwang mehr besteht, direkt weiterleiten
        if not user.get("password_must_change", False):
            if session.get("role") == "admin":
                return redirect(url_for("admin_panel"))
            return redirect(url_for("user_home"))

        error = None

        if request.method == "POST":
            new_pw = (request.form.get("new_password") or "").strip()
            repeat_pw = (request.form.get("new_password_repeat") or "").strip()

            if not new_pw:
                error = "Bitte ein neues Passwort eingeben."
            elif new_pw != repeat_pw:
                error = "Die beiden Passwörter stimmen nicht überein."
            else:
                # Neues Passwort setzen, Zwang zurücknehmen
                user["password"] = new_pw
                user["password_must_change"] = False
                user["password_set_at"] = datetime.now().isoformat(timespec="seconds")
                save_userlist(userlist)

                # Danach normale Weiterleitung
                if session.get("role") == "admin":
                    return redirect(url_for("admin_panel"))
                return redirect(url_for("user_home"))

        return render_template("change_password.html", error=error)

    # ==========================================================
    # LOGOUT
    # ==========================================================
    @app.route("/logout")
    def logout():
        """Beendet die aktuelle Sitzung und kehrt zur Login-Seite zurück."""
        session.clear()
        return redirect(url_for("login"))

    # ==========================================================
    # ERSTINSTALLATION / ADMIN-SETUP
    # ==========================================================
    @app.route("/setup_admin", methods=["GET", "POST"])
    def setup_admin():
        """
        Einrichtungsseite für den allerersten Administrator.
        Nur erreichbar, solange es noch keinen Admin in der userlist gibt.
        """
        userlist = load_userlist() or {}

        # Wenn inzwischen ein Admin existiert, zurück zum normalen Login
        if any(u.get("role") == "admin" for u in userlist.values()):
            return redirect(url_for("login"))

        error = None

        if request.method == "POST":
            # Passwort ist hier Pflicht
            ok, error, data = parse_user_form(request.form, password_required=True)

            if ok:
                # Rolle unabhängig vom Formular immer auf "admin" setzen
                add_user(
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    nfc_code=data["nfc_code"],
                    password=data["password"],
                    role="admin",
                )
                return redirect(url_for("login"))

        # GET oder POST mit Fehler -> Setup-Seite anzeigen
        return render_template("setup_admin.html", error=error)
