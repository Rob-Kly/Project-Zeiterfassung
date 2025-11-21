import os
from datetime import datetime, timedelta
from calendar import monthrange

from flask import render_template, redirect, url_for, session

from zfa_io import load_userlist, load_timestamps
from worktime_report import get_worked_hours

"""
Routen für den Mitarbeiterbereich:

- /user_home
"""


def init_user_routes(app):
    print("   → init_user_routes() aufgerufen")

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

        # Falls Passwort noch geändert werden muss → zuerst auf /change_password
        userlist = load_userlist()
        current_user = userlist.get(user_id)
        if current_user and current_user.get("password_must_change") is True:
            return redirect(url_for("change_password"))

        name = session.get("name", "Unbekannt")

        user_folder = current_user["folder"]
        timestamps_path = os.path.join(user_folder, f"{user_folder}_timestamps.txt")
        timestamps = load_timestamps(timestamps_path)

        today = datetime.now().date()
        today_str = today.strftime("%Y-%m-%d")
        today_entries = [ts for ts in timestamps if ts["time"].startswith(today_str)]

        # Arbeitszeiten berechnen
        today_hours = get_worked_hours(user_id, today_str, today_str)["total_hm"]

        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        week_hours = get_worked_hours(
            user_id,
            monday.strftime("%Y-%m-%d"),
            sunday.strftime("%Y-%m-%d"),
        )["total_hm"]

        year, month = today.year, today.month
        last_day = monthrange(year, month)[1]
        month_hours = get_worked_hours(
            user_id,
            f"{year}-{month:02d}-01",
            f"{year}-{month:02d}-{last_day:02d}",
        )["total_hm"]

        return render_template(
            "user_home.html",
            name=name,
            user_id=user_id,
            timestamps=today_entries,
            today_hours=today_hours,
            week_hours=week_hours,
            month_hours=month_hours,
        )
