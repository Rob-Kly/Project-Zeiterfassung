#!/usr/bin/env python3
import tkinter as tk
from datetime import datetime, timedelta, time
import subprocess
import time as pytime  # um Konflikt mit datetime.time zu vermeiden

def set_system_time(dt: datetime) -> None:
    """Setzt die Systemzeit auf den übergebenen Zeitpunkt."""
    new_time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    old_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    status_var.set(f"Alte Zeit: {old_time_str}\nNeue Zeit: {new_time_str}")
    root.update_idletasks()

    try:
        # NTP deaktivieren, damit die Zeit nicht direkt wieder zurückspringt
        subprocess.run(["timedatectl", "set-ntp", "false"], check=False)
        subprocess.run(["timedatectl", "set-time", new_time_str], check=True)
    except FileNotFoundError:
        # Falls timedatectl nicht vorhanden ist, auf 'date -s' zurückfallen
        try:
            subprocess.run(["date", "-s", new_time_str], check=True)
        except subprocess.CalledProcessError as e:
            status_var.set(f"Fehler beim Setzen der Zeit (date -s): {e}")
            return
    except subprocess.CalledProcessError as e:
        status_var.set(f"Fehler beim Setzen der Zeit (timedatectl): {e}")
        return

    # Nach erfolgreichem Setzen einmal direkt aktualisieren
    clock_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    root.update_idletasks()

def jump_hours(hours: int) -> None:
    now = datetime.now()
    target = now + timedelta(hours=hours)
    set_system_time(target)

def jump_days(days: int) -> None:
    # Datum verschieben, Uhrzeit immer 09:00:00
    today = datetime.now().date() + timedelta(days=days)
    target = datetime.combine(today, time(9, 0, 0))
    set_system_time(target)

def jump_months(months: int) -> None:
    # Erster Tag des (aktuellen Monat +/- months), 09:00:00
    now = datetime.now()
    month_index = (now.month - 1) + months
    year = now.year + month_index // 12
    month = (month_index % 12) + 1
    target = datetime(year, month, 1, 9, 0, 0)
    set_system_time(target)

# ------------------ GUI-Aufbau ------------------

root = tk.Tk()
root.title("Zeitsprung-Steuerung")

clock_var = tk.StringVar()
status_var = tk.StringVar()

# Oben: aktuelle Zeit
clock_label = tk.Label(root, textvariable=clock_var, font=("Arial", 16))
clock_label.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

# Zeile 1: Stunden
btn_plus1h = tk.Button(root, text="+1 Stunde", command=lambda: jump_hours(1))
btn_minus1h = tk.Button(root, text="-1 Stunde", command=lambda: jump_hours(-1))
btn_plus5h = tk.Button(root, text="+5 Stunden", command=lambda: jump_hours(5))
btn_minus5h = tk.Button(root, text="-5 Stunden", command=lambda: jump_hours(-5))

btn_plus1h.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
btn_minus1h.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
btn_plus5h.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
btn_minus5h.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

# Zeile 2: Tage / Monate
btn_plus1d = tk.Button(root, text="+1 Tag (09:00)", command=lambda: jump_days(1))
btn_minus1d = tk.Button(root, text="-1 Tag (09:00)", command=lambda: jump_days(-1))
btn_plus1m = tk.Button(root, text="+1 Monat (1., 09:00)", command=lambda: jump_months(1))
btn_minus1m = tk.Button(root, text="-1 Monat (1., 09:00)", command=lambda: jump_months(-1))

btn_plus1d.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
btn_minus1d.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
btn_plus1m.grid(row=2, column=2, padx=5, pady=5, sticky="ew")
btn_minus1m.grid(row=2, column=3, padx=5, pady=5, sticky="ew")

# Unten: Statusausgabe
status_label = tk.Label(root, textvariable=status_var, justify="left")
status_label.grid(row=3, column=0, columnspan=4, padx=10, pady=10)

# ------------------ Haupt-Loop manuell steuern ------------------

def main_loop():
    while True:
        # Uhr immer aus aktueller Systemzeit setzen
        clock_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        try:
            root.update_idletasks()
            root.update()
        except tk.TclError:
            # Fenster wurde geschlossen -> Programm sauber beenden
            break
        pytime.sleep(1)

if __name__ == "__main__":
    main_loop()

