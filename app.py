from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from timeclock import clock, DEFAULT_WORK_START, DEFAULT_WORK_END, get_pending_corrections_for_user
from timesheet import get_monthly_report, get_worked_hours
from zfa_utils import (
    load_userlist,
    load_timestamps,
    get_pending_corrections_flag,
    set_pending_corrections_flag,
)
from user_management import add_user, remove_user, update_user
from datetime import datetime, timedelta
from calendar import monthrange
import os, json

# ==========================================================
# FLASK BASIS
# ==========================================================
app = Flask(__name__)
app.secret_key = "zeiterfassung_secret_key"
SESSION_TIMEOUT = 300  # Sekunden (Inaktivität = 5 Minuten)

# ==========================================================
# ROOT → LOGIN
# ==========================================================
@app.route("/")
def root_redirect():
    """Leitet die Hauptadresse direkt zur Login-Seite weiter."""
    return redirect(url_for("login"))

# ==========================================================
# LOGIN UND LOGOUT
# ==========================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login-Seite für Benutzer und Administratoren.
    Benutzername = 'Vorname Nachname', Passwort laut userlist.txt.
    """
    userlist = load_userlist()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        for user_id, user in userlist.items():
            full_name = f"{user['first_name']} {user['last_name']}"
            if username == full_name and user.get("password") == password:
                session["user_id"] = user_id
                session["role"] = user.get("role", "user")
                session["name"] = full_name

                # Weiterleitung nach Rolle
                if session["role"] == "admin":
                    return redirect(url_for("admin_panel"))
                return redirect(url_for("user_home"))

        return render_template("login.html", error="Falscher Benutzername oder Passwort.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Beendet die aktuelle Sitzung und kehrt zur Login-Seite zurück."""
    session.clear()
    return redirect(url_for("login"))

# ==========================================================
# MITARBEITERSEITE
# ==========================================================
@app.route("/user_home")
def user_home():
    """
    Zeigt die eigene Übersichtsseite eines Mitarbeiters
    mit Tages-, Wochen- und Monatsarbeitszeiten.
    """
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    name = session.get("name", "Unbekannt")

    user_folder = f"user_{user_id}"
    timestamps_path = os.path.join(user_folder, f"{user_folder}_timestamps.txt")
    timestamps = load_timestamps(timestamps_path)

    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
    today_entries = [ts for ts in timestamps if ts["time"].startswith(today_str)]

    # Arbeitszeiten berechnen
    today_hours = get_worked_hours(user_id, today_str, today_str)["total_hm"]
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    week_hours = get_worked_hours(user_id, monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d"))["total_hm"]

    year, month = today.year, today.month
    last_day = monthrange(year, month)[1]
    month_hours = get_worked_hours(user_id, f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day:02d}")["total_hm"]

    return render_template(
        "user_home.html",
        name=name,
        user_id=user_id,
        timestamps=today_entries,
        today_hours=today_hours,
        week_hours=week_hours,
        month_hours=month_hours
    )

# ==========================================================
# ADMINBEREICH – HAUPTÜBERSICHT
# ==========================================================
@app.route("/admin_panel")
def admin_panel():
    """
    Startseite für Administratoren mit Benutzerübersicht,
    Monatsreport und optionaler Warnmeldung bei neuen
    automatisch gesetzten Buchungen.
    """
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    userlist = load_userlist()
    now = datetime.now()
    year, month = now.year, now.month
    report = get_monthly_report(year, month)
    has_pending_corrections = get_pending_corrections_flag()

    return render_template(
        "admin_panel.html",
        name=session.get("name", "Admin"),
        users=userlist,
        report=report,
        has_pending_corrections=has_pending_corrections,
        admin_id=session["user_id"]  # Für An-/Abmeldebutton im Adminpanel
    )

# ==========================================================
# ADMINBEREICH – NUTZER ERSTELLEN / BEARBEITEN / LÖSCHEN
# ==========================================================
@app.route("/admin/add_user", methods=["POST"])
def admin_add_user():
    """Erstellt einen neuen Benutzer über das Formular im Adminbereich."""
    if "role" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    data = request.form
    add_user(
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        nfc_code=data.get("nfc_code"),
        password=data.get("password"),
        role=data.get("role", "user")
    )
    return redirect(url_for("admin_panel"))


@app.route("/admin/edit_user/<user_id>", methods=["GET", "POST"])
def admin_edit_user(user_id):
    """Bearbeitet die Daten eines bestehenden Nutzers."""
    if "role" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    userlist = load_userlist()
    user = userlist.get(user_id)
    if not user:
        return "Unbekannte User-ID", 404

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        nfc_code = request.form.get("nfc_code")
        password = request.form.get("password")
        role = request.form.get("role")
        if not password:
            password = None

        update_user(user_id, first_name=first_name, last_name=last_name,
                    nfc_code=nfc_code, password=password, role=role)
        return redirect(url_for("admin_panel"))

    return render_template("edit_user.html", user_id=user_id, user=user)


@app.route("/admin/remove_user/<user_id>")
def admin_remove_user(user_id):
    """Entfernt einen Nutzer aus der Liste (sein Ordner bleibt bestehen)."""
    if "role" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))
    remove_user(user_id)
    return redirect(url_for("admin_panel"))

# ==========================================================
# ADMINBEREICH – DETAILANSICHT EINES MITARBEITERS
# ==========================================================
@app.route("/admin/user/<user_id>")
def admin_view_user(user_id):
    """
    Zeigt als Administrator die Tages-, Wochen- und Monatsübersicht
    eines bestimmten Mitarbeiters (nur Lesemodus).
    """
    if "role" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    userlist = load_userlist()
    user = userlist.get(user_id)
    if not user:
        return "Unbekannter Benutzer", 404

    name = f"{user['first_name']} {user['last_name']}"
    user_folder = user["folder"]
    timestamps_path = os.path.join(user_folder, f"{user['folder']}_timestamps.txt")
    timestamps = load_timestamps(timestamps_path)

    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
    today_entries = [ts for ts in timestamps if ts["time"].startswith(today_str)]

    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    year, month = today.year, today.month
    last_day = monthrange(year, month)[1]

    today_hours = get_worked_hours(user_id, today_str, today_str)["total_hm"]
    week_hours = get_worked_hours(user_id, monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d"))["total_hm"]
    month_hours = get_worked_hours(user_id, f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day:02d}")["total_hm"]

    return render_template(
        "user_home.html",
        name=f"{name} (Admin-Ansicht)",
        user_id=user_id,
        timestamps=today_entries,
        today_hours=today_hours,
        week_hours=week_hours,
        month_hours=month_hours
    )

# ==========================================================
# ADMINBEREICH – FEHLERZEITEN / AUTO-KORREKTUREN
# ==========================================================
@app.route("/admin/fix_errors")
def fix_errors():
    """
    Zeigt alle automatisch gesetzten Einträge (Auto-Login/Auto-Logout)
    und ermöglicht deren Korrektur. Löscht das Warnflag nach dem Öffnen.
    """
    if "role" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    # Flag zurücksetzen, sobald der Admin die Seite öffnet
    set_pending_corrections_flag(False)

    userlist = load_userlist()
    candidates = {}
    for uid in userlist.keys():
        entries = get_pending_corrections_for_user(uid)
        if entries:
            candidates[uid] = {
                "name": f"{userlist[uid]['first_name']} {userlist[uid]['last_name']}",
                "entries": entries
            }

    return render_template(
        "fix_errors.html",
        candidates=candidates,
        start_h=f"{DEFAULT_WORK_START[0]:02d}:{DEFAULT_WORK_START[1]:02d}",
        end_h=f"{DEFAULT_WORK_END[0]:02d}:{DEFAULT_WORK_END[1]:02d}"
    )

# ==========================================================
# API: AN-/ABMELDUNG
# ==========================================================
@app.route("/api/clock", methods=["POST"])
def api_clock():
    """
    Wird von der Weboberfläche (JavaScript) aufgerufen,
    um eine An- oder Abmeldung auszulösen.
    """
    data = request.get_json(silent=True)
    if not data or "user_id" not in data:
        return jsonify({"error": "user_id fehlt"}), 400

    user_id = str(data["user_id"])
    message = clock(user_id)
    return jsonify({"message": message}), 200

# ==========================================================
# SERVERSTART
# ==========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
