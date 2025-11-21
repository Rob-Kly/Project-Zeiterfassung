import os
import json
import re
from datetime import datetime, timedelta
from calendar import monthrange

from flask import (
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    session,
)

from attendance import clock, get_pending_corrections_for_user
from worktime_report import get_monthly_report, get_worked_hours
from zfa_io import load_userlist, load_timestamps, save_timestamps
from zfa_flags import get_pending_corrections_flag, set_pending_corrections_flag
from zfa_passwords import parse_user_form
from user_management import add_user, remove_user, update_user, find_user_by_nfc
from config import DEFAULT_WORK_START, DEFAULT_WORK_END, REPORTS_DIR


"""
Routen für den Adminbereich:

- /admin_panel
- /admin/add_user
- /admin/edit_user/<user_id>
- /admin/remove_user/<user_id>
- /admin/user/<user_id>
- /admin/fix_errors
- /admin/fix_errors/apply
- /admin/reports
- /admin/reports/<year>/<month>

sowie API-Endpunkte:

- /api/clock
- /api/pending_nfc
"""


def init_admin_routes(app):
    print("   → init_admin_routes() aufgerufen")
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

        # Admin muss ggf. zuerst sein Passwort ändern
        admin_user = userlist.get(session["user_id"])
        if admin_user and admin_user.get("password_must_change") is True:
            return redirect(url_for("change_password"))

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
            admin_id=session["user_id"],  # Für An-/Abmeldebutton im Adminpanel
        )

    # ==========================================================
    # ADMINBEREICH – NUTZER ERSTELLEN / BEARBEITEN / LÖSCHEN
    # ==========================================================
    @app.route("/admin/add_user", methods=["POST"])
    def admin_add_user():
        """Erstellt einen neuen Benutzer über das Formular im Adminbereich."""
        if "role" not in session or session.get("role") != "admin":
            return redirect(url_for("login"))

        ok, error, data = parse_user_form(request.form, password_required=True)

        # Nur prüfen, wenn die Basis-Validierung durch ist
        if not error and ok:
            nfc = data["nfc_code"]
            if nfc:
                other_id, other_user = find_user_by_nfc(nfc)
                if other_id is not None:
                    error = (
                        f"Dieser NFC-Code ist bereits dem Benutzer "
                        f"{other_user['first_name']} {other_user['last_name']} "
                        f"(ID {other_id}) zugeordnet."
                    )
                    ok = False

        if error or not ok:
            # Adminpanel mit Fehlermeldung neu rendern
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
                admin_id=session["user_id"],
                error=error,
            )

        # alles okay → Nutzer anlegen
        add_user(
            first_name=data["first_name"],
            last_name=data["last_name"],
            nfc_code=data["nfc_code"],
            password=data["password"],
            role=data["role"],
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
            ok, error, data = parse_user_form(request.form, password_required=False)

            # Zusatz: NFC-Code auf Doppelvergabe prüfen
            if not error and ok:
                nfc = data["nfc_code"]
                if nfc:
                    other_id, other_user = find_user_by_nfc(nfc, exclude_user_id=user_id)
                    if other_id is not None:
                        error = (
                            f"Dieser NFC-Code ist bereits dem Benutzer "
                            f"{other_user['first_name']} {other_user['last_name']} "
                            f"(ID {other_id}) zugeordnet."
                        )
                        ok = False

            if error or not ok:
                return render_template(
                    "edit_user.html",
                    user_id=user_id,
                    user=user,
                    error=error,
                )

            update_user(
                user_id,
                first_name=data["first_name"],
                last_name=data["last_name"],
                nfc_code=data["nfc_code"],
                password=data["password"],  # None = keine Änderung
                role=data["role"],
            )
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
        week_hours = get_worked_hours(
            user_id,
            monday.strftime("%Y-%m-%d"),
            sunday.strftime("%Y-%m-%d"),
        )["total_hm"]
        month_hours = get_worked_hours(
            user_id,
            f"{year}-{month:02d}-01",
            f"{year}-{month:02d}-{last_day:02d}",
        )["total_hm"]

        return render_template(
            "user_home.html",
            name=f"{name} (Admin-Ansicht)",
            user_id=user_id,
            timestamps=today_entries,
            today_hours=today_hours,
            week_hours=week_hours,
            month_hours=month_hours,
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
                    "entries": entries,
                }

        return render_template(
            "fix_errors.html",
            candidates=candidates,
            start_h=f"{DEFAULT_WORK_START[0]:02d}:{DEFAULT_WORK_START[1]:02d}",
            end_h=f"{DEFAULT_WORK_END[0]:02d}:{DEFAULT_WORK_END[1]:02d}",
        )

    @app.route("/admin/fix_errors/apply", methods=["POST"])
    def apply_fix_error():
        """Übernimmt eine Korrektur oder akzeptiert einen Auto-Eintrag unverändert."""
        if "role" not in session or session.get("role") != "admin":
            return redirect(url_for("login"))

        user_id = request.form.get("user_id")
        date_str = request.form.get("date")  # Format: YYYY-MM-DD
        type_ = request.form.get("type")  # "in" oder "out"
        action = request.form.get("action", "save")
        new_time_str = (request.form.get("new_time") or "").strip()

        if not user_id or not date_str or not type_:
            return redirect(url_for("fix_errors"))

        # Timestamp-Datei des Nutzers laden
        userlist = load_userlist()
        user = userlist.get(user_id)
        if not user:
            return redirect(url_for("fix_errors"))

        path = os.path.join(user["folder"], f"{user['folder']}_timestamps.txt")
        timestamps = load_timestamps(path)

        # Gesuchten Eintrag finden
        for entry in timestamps:
            try:
                dt = datetime.strptime(entry["time"], "%Y-%m-%d %H:%M:%S")
            except (KeyError, ValueError):
                continue

            if entry.get("type") != type_:
                continue

            if dt.strftime("%Y-%m-%d") != date_str:
                continue

            # Wir haben den passenden Auto-Eintrag gefunden
            if action == "accept":
                # Eintrag unverändert lassen, aber als 'akzeptiert' markieren
                entry["auto_confirmed"] = True
            else:
                # Neue Uhrzeit übernehmen (HH:MM), Datum des Eintrags beibehalten
                if new_time_str:
                    try:
                        hh, mm = map(int, new_time_str.split(":"))
                        new_dt = dt.replace(hour=hh, minute=mm, second=0)
                        entry["time"] = new_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        # Ungültige Eingabe -> wir ignorieren sie einfach und lassen alles wie vorher
                        pass
            break

        # Änderungen speichern
        save_timestamps(path, timestamps)

        # Zurück zur Übersicht
        return redirect(url_for("fix_errors"))

    # ==========================================================
    # ADMINBEREICH – REPORTSEITE
    # ==========================================================
    @app.route("/admin/reports")
    def admin_reports_list():
        """Liste aller vorhandenen Monatsreports aus dem Ordner REPORTS_DIR."""
        if "user_id" not in session or session.get("role") != "admin":
            return redirect(url_for("login"))

        reports = []
        if os.path.isdir(REPORTS_DIR):
            for fname in os.listdir(REPORTS_DIR):
                m = re.match(r"monthly_report_(\d{4})_(\d{2})\.txt$", fname)
                if m:
                    year = int(m.group(1))
                    month = int(m.group(2))
                    reports.append(
                        {
                            "year": year,
                            "month": month,
                            "filename": fname,
                        }
                    )

        # Neueste zuerst
        reports.sort(key=lambda r: (r["year"], r["month"]), reverse=True)

        return render_template("reports_list.html", reports=reports)

    @app.route("/admin/reports/<int:year>/<int:month>")
    def admin_view_report(year, month):
        """Zeigt einen gespeicherten Monatsreport aus REPORTS_DIR als Tabelle an."""
        if "user_id" not in session or session.get("role") != "admin":
            return redirect(url_for("login"))

        filename = os.path.join(REPORTS_DIR, f"monthly_report_{year}_{month:02d}.txt")
        if not os.path.exists(filename):
            return f"Report {month:02d}/{year} nicht gefunden.", 404

        with open(filename, "r", encoding="utf-8") as f:
            report = json.load(f)

        return render_template("admin_report_view.html", report=report)

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
    # API: NFC (Pending letzte Karte)
    # ==========================================================
    @app.route("/api/pending_nfc")
    def api_pending_nfc():
        """
        Liefert den zuletzt eingelesenen NFC-Code aus pending_nfc.json
        und löscht die Datei danach, damit der Code nur einmal verwendet werden kann.
        """
        path = "pending_nfc.json"
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                try:
                    os.remove(path)
                except OSError:
                    pass
                return jsonify({"nfc_code": None}), 200

            try:
                os.remove(path)
            except OSError:
                pass

            return jsonify(data), 200

        return jsonify({"nfc_code": None}), 200
