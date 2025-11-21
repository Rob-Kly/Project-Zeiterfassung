from flask import Flask, request, redirect, url_for, session
from datetime import datetime

from config import SESSION_TIMEOUT

from routes_auth import init_auth_routes
from routes_user import init_user_routes
from routes_admin import init_admin_routes

"""
Zentrale App-Initialisierung.

Aufgaben:
- Flask-App erstellen
- Session-Timeout erzwingen
- Routen aus den Teilmodulen registrieren
"""

# ==========================================================
# FLASK BASIS
# ==========================================================
app = Flask(__name__)
app.secret_key = "zeiterfassung_secret_key"


# ==========================================================
# SESSION-TIMEOUT
# ==========================================================
@app.before_request
def enforce_session_timeout():
    """
    Erzwingt einen automatischen Logout nach SESSION_TIMEOUT Sekunden Inaktivität.
    """
    # Login und statische Dateien nicht umlenken
    if request.endpoint in ("login", "static"):
        return

    user_id = session.get("user_id")
    if not user_id:
        # Nicht eingeloggt → nichts zu tun
        return

    now = datetime.now()
    last_str = session.get("last_activity")

    if last_str:
        try:
            last = datetime.fromisoformat(last_str)
        except ValueError:
            # Falls der gespeicherte Wert kaputt ist → Session sicherheitshalber beenden
            session.clear()
            return redirect(url_for("login", reason="timeout"))

        if (now - last).total_seconds() > SESSION_TIMEOUT:
            # Timeout abgelaufen → Session löschen und zur Loginseite mit Hinweis
            session.clear()
            return redirect(url_for("login", reason="timeout"))

    # Aktuelle Aktivität speichern
    session["last_activity"] = now.isoformat(timespec="seconds")


# ==========================================================
# ROUTEN REGISTRIEREN
# ==========================================================
print("👉 Registriere Routen ...")
init_auth_routes(app)
init_user_routes(app)
init_admin_routes(app)
print("✅ Routen initialisiert.")


# ==========================================================
# SERVERSTART
# ==========================================================
if __name__ == "__main__":
    print("🚀 Starte Flask-Server auf 0.0.0.0:8080 ...")
    app.run(host="0.0.0.0", port=8080, debug=True)
