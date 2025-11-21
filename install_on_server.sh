#!/usr/bin/env bash
# install_on_server.sh
# Einmal ausführen, um Zeiterfassung als Systemdienst auf diesem Server einzurichten.

set -e

# Ordner des Projekts (dort, wo dieses Script liegt)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_USER="$(whoami)"

echo "Projektpfad : $PROJECT_DIR"
echo "Service-User: $SERVICE_USER"
echo

# ----------------------------------------------------------
# 1) Python venv anlegen + Pakete installieren
# ----------------------------------------------------------
if [ ! -d "$PROJECT_DIR/.venv" ]; then
  echo "➜ Erzeuge Python-venv ..."
  python3 -m venv "$PROJECT_DIR/.venv"
  "$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
  "$PROJECT_DIR/.venv/bin/pip" install flask nfcpy
else
  echo "✓ venv existiert bereits, überspringe Erzeugung."
fi

# ----------------------------------------------------------
# 2) Dateirechte einschränken (nur dieser User)
# ----------------------------------------------------------
echo "➜ Setze Dateirechte im Projektordner (nur $SERVICE_USER) ..."
chmod 700 "$PROJECT_DIR"
find "$PROJECT_DIR" -type d -exec chmod 700 {} \;
find "$PROJECT_DIR" -type f -exec chmod 600 {} \;

# ----------------------------------------------------------
# 3) systemd-Service: Flask-App
# ----------------------------------------------------------
echo "➜ Erzeuge / aktualisiere systemd-Unit: zeiterfassung.service ..."
sudo tee /etc/systemd/system/zeiterfassung.service >/dev/null <<EOF
[Unit]
Description=EBC Zeiterfassung Flask App
After=network-online.target
Wants=network-online.target

[Service]
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# ----------------------------------------------------------
# 4) systemd-Service: NFC-Listener
# ----------------------------------------------------------
echo "➜ Erzeuge / aktualisiere systemd-Unit: zeiterfassung-nfc.service ..."
sudo tee /etc/systemd/system/zeiterfassung-nfc.service >/dev/null <<EOF
[Unit]
Description=EBC Zeiterfassung NFC Listener
After=zeiterfassung.service
Requires=zeiterfassung.service

[Service]
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/nfc_listener.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# ----------------------------------------------------------
# 5) systemd-Service + Timer: Auto-Reports (Vormonat)
# ----------------------------------------------------------
echo "➜ Erzeuge / aktualisiere systemd-Unit: zeiterfassung-reports.service ..."
sudo tee /etc/systemd/system/zeiterfassung-reports.service >/dev/null <<EOF
[Unit]
Description=EBC Zeiterfassung Monatsreport (Vormonat)

[Service]
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/auto_reports.py
EOF

echo "➜ Erzeuge / aktualisiere systemd-Timer: zeiterfassung-reports.timer ..."
sudo tee /etc/systemd/system/zeiterfassung-reports.timer >/dev/null <<EOF
[Unit]
Description=EBC Zeiterfassung Monatsreport Timer

[Timer]
OnCalendar=monthly
Persistent=true

[Install]
WantedBy=timers.target
EOF

# ----------------------------------------------------------
# 6) systemd neu laden & Dienste aktivieren
# ----------------------------------------------------------
echo "➜ Lade systemd neu und aktiviere Dienste/Timer ..."
sudo systemctl daemon-reload

sudo systemctl enable zeiterfassung.service
sudo systemctl enable zeiterfassung-nfc.service
sudo systemctl enable zeiterfassung-reports.timer

sudo systemctl start zeiterfassung.service
sudo systemctl start zeiterfassung-nfc.service
sudo systemctl start zeiterfassung-reports.timer

echo
echo "✅ Installation abgeschlossen."
echo " - Web-App   läuft als Service: zeiterfassung.service"
echo " - NFC       läuft als Service: zeiterfassung-nfc.service"
echo " - AutoReport-Timer: zeiterfassung-reports.timer"
echo
echo "Status prüfen z.B. mit:"
echo "  sudo systemctl status zeiterfassung.service"
echo "  sudo systemctl status zeiterfassung-nfc.service"
echo "  sudo systemctl status zeiterfassung-reports.timer"
