from flask import Flask, request, jsonify, render_template, redirect, url_for, session, g
from timeclock import clock, DEFAULT_WORK_START, DEFAULT_WORK_END
from timesheet import get_monthly_report, get_worked_hours
from zfa_utils import load_userlist, load_timestamps, save_timestamps
from user_management import add_user, remove_user, update_user
from datetime import datetime, timedelta
from calendar import monthrange
import os, json

app = Flask(__name__)
app.secret_key = "zeiterfassung_secret_key"  # TODO: In Produktion sicher speichern

# Sitzung läuft 5 Minuten (300 Sekunden)
SESSION_TIMEOUT = 300  # Sekunden


# ==========================================================
# STARTSEITE (Root)
# ==========================================================
@app.route("/")
def index():
    """
    Leitet automatisch zur passenden Seite weiter:
    - Admin → Admin-Panel
    - Benutzer → Benutzer-Startseite
    - Nicht eingeloggt → Login-Seite
    """
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_panel"))
        else:
            return redirect(url_for("user_home"))
    return redirect(url_for("login"))


# ==========================================================
# SESSION HANDLING / TIMEOUT
# ==========================================================
@app.before_request
def session_timeout_check():
    """Beendet Sitzung nach 5 Minuten Inaktivität."""
    now = datetime.now().timestamp()
    last_active = session.get("last_active")

    # Wenn es eine aktive Session gibt, aber Timeout überschritten ist
    if last_active and (now - last_active > SESSION_TIMEOUT):
        session.clear()
        return redirect(url_for("login"))

    # Zeitstempel aktualisieren, wenn der Benutzer aktiv ist
    if "user_id" in session:
        session["last_active"] = now


# ==========================================================
# LOGIN & LOGOUT
# ==========================================================
@app.route("/login", methods=["GET", "POST"])
def login():
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

                if session["role"] == "admin":
                    return redirect(url_for("admin_panel"))
                else:
                    return redirect(url_for("user_home"))

        return render_template("login.html", error="Falscher Benutzername oder Passwort.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==========================================================
# MITARBEITERSEITE
# ==========================================================
@app.route("/user_home")
def user_home():
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
    today_report = get_worked_hours(user_id, today_str, today_str)
    today_hours = today_report["total_hm"]

    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    week_report = get_worked_hours(user_id, monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d"))
    week_hours = week_report["total_hm"]

    year, month = today.year, today.month
    last_day = monthrange(year, month)[1]
    month_report = get_worked_hours(user_id, f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day:02d}")
    month_hours = month_report["total_hm"]

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
# ADMIN: PANEL (Übersicht, Reports, Nutzerverwaltung)
# ==========================================================
@app.route("/admin_panel")
def admin_panel():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    userlist = load_userlist()
    now = datetime.now()
    year, month = now.year, now.month
    report = get_monthly_report(year, month)

    return render_template(
        "admin_panel.html",
        name=session.get("name", "Admin"),
        users=userlist,
        report=report
    )


# ==========================================================
# ADMIN: Nutzer anlegen (automatische ID)
# ==========================================================
@app.route("/admin/add_user", methods=["POST"])
def admin_add_user():
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


# ==========================================================
# ADMIN: Nutzer bearbeiten
# ==========================================================
@app.route("/admin/edit_user/<user_id>", methods=["GET", "POST"])
def admin_edit_user(user_id):
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


# ==========================================================
# ADMIN: Nutzer löschen
# ==========================================================
@app.route("/admin/remove_user/<user_id>")
def admin_remove_user(user_id):
    if "role" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))
    remove_user(user_id)
    return redirect(url_for("admin_panel"))


# ==========================================================
# ADMIN: Nutzer-Detailansicht (Arbeitszeiten / Buchungen)
# ==========================================================
@app.route("/admin/user/<user_id>")
def admin_view_user(user_id):
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
# ADMIN: Fehlerzeiten-Korrektur (Auto-Login / Auto-Logout)
# ==========================================================
def _find_auto_entries_for_user(user_id: str):
    """Liefert korrigierbare Auto-Einträge für einen Nutzer."""
    userlist = load_userlist()
    user = userlist.get(user_id)
    if not user:
        return []

    path = os.path.join(user["folder"], f"{user['folder']}_timestamps.txt")
    ts = load_timestamps(path)
    results = []
    for entry in ts:
        dt = datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")
        hhmmss = dt.strftime("%H:%M:%S")
        if (entry["type"] == "in" and hhmmss == f"{DEFAULT_WORK_START[0]:02d}:{DEFAULT_WORK_START[1]:02d}:{DEFAULT_WORK_START[2]:02d}") \
           or (entry["type"] == "out" and hhmmss == f"{DEFAULT_WORK_END[0]:02d}:{DEFAULT_WORK_END[1]:02d}:{DEFAULT_WORK_END[2]:02d}"):
            results.append({"type": entry["type"], "date": dt.strftime("%Y-%m-%d")})
    return results


@app.route("/admin/fix_errors", methods=["GET"])
def fix_errors():
    if "role" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    userlist = load_userlist()
    candidates = {}
    for uid in userlist.keys():
        entries = _find_auto_entries_for_user(uid)
        if entries:
            candidates[uid] = {
                "name": f"{userlist[uid]['first_name']} {userlist[uid]['last_name']}",
                "entries": entries
            }

    return render_template("fix_errors.html", candidates=candidates,
                           start_h=f"{DEFAULT_WORK_START[0]:02d}:{DEFAULT_WORK_START[1]:02d}",
                           end_h=f"{DEFAULT_WORK_END[0]:02d}:{DEFAULT_WORK_END[1]:02d}")


@app.route("/admin/fix_errors/apply", methods=["POST"])
def apply_fix_error():
    if "role" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    user_id = request.form.get("user_id")
    date = request.form.get("date")
    etype = request.form.get("type")
    new_time = request.form.get("new_time")

    userlist = load_userlist()
    user = userlist.get(user_id)
    if not user:
        return "Unbekannter Benutzer", 400

    path = os.path.join(user["folder"], f"{user['folder']}_timestamps.txt")
    ts = load_timestamps(path)

    target_hms = None
    if etype == "in":
        target_hms = f"{DEFAULT_WORK_START[0]:02d}:{DEFAULT_WORK_START[1]:02d}:{DEFAULT_WORK_START[2]:02d}"
    elif etype == "out":
        target_hms = f"{DEFAULT_WORK_END[0]:02d}:{DEFAULT_WORK_END[1]:02d}:{DEFAULT_WORK_END[2]:02d}"
    else:
        return "Ungültiger Typ", 400

    try:
        new_dt_str = f"{date} {new_time}:00"
        datetime.strptime(new_dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return "Ungültiges Zeitformat", 400

    changed = False
    for entry in ts:
        dt = datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")
        if entry["type"] == etype and dt.strftime("%Y-%m-%d") == date and dt.strftime("%H:%M:%S") == target_hms:
            entry["time"] = new_dt_str
            changed = True
            break

    if not changed:
        return "Kein automatisch gesetzter Eintrag für diese Auswahl gefunden.", 400

    save_timestamps(path, ts)
    return redirect(url_for("fix_errors"))


# ==========================================================
# API-ENDPUNKTE
# ==========================================================
@app.route("/api/clock", methods=["POST"])
def api_clock():
    data = request.get_json(silent=True)
    if not data or "user_id" not in data:
        return jsonify({"error": "user_id fehlt"}), 400

    user_id = str(data["user_id"])
    message = clock(user_id)
    return jsonify({"message": message}), 200


@app.route("/api/users", methods=["GET"])
def api_users():
    return jsonify(load_userlist()), 200


@app.route("/api/reports", methods=["GET"])
def api_reports():
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    if not year or not month:
        now = datetime.now()
        year, month = now.year, now.month
    return jsonify(get_monthly_report(year, month)), 200


@app.route("/api/pending_nfc")
def api_pending_nfc():
    """Liest den zuletzt eingelesenen NFC-Code aus und löscht ihn danach."""
    pending_path = "pending_nfc.json"

    if os.path.exists(pending_path):
        try:
            with open(pending_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Datei löschen, nachdem der Code übertragen wurde
            os.remove(pending_path)
            print("🧹 pending_nfc.json wurde nach Übertragung gelöscht.")
            return jsonify(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️ Fehler beim Lesen/Löschen von pending_nfc.json: {e}")
            return jsonify({"nfc_code": None})
    else:
        return jsonify({"nfc_code": None})


# ==========================================================
# SERVERSTART
# ==========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
