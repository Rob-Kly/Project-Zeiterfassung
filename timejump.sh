#!/usr/bin/env bash

# Enterprise-Version: Komfortables Zeitsprung-Menü für Demo/Präsentation
# Nutzung: sudo ./timejump_enterprise.sh

set -e

if [[ "$EUID" -ne 0 ]]; then
  echo "Bitte als root starten (z.B. mit: sudo $0)"
  exit 1
fi

set_system_time() {
  local new_time="$1"
  local old_time
  old_time=$(date '+%Y-%m-%d %H:%M:%S')

  echo
  echo "--------------------------------------"
  echo " Alte Systemzeit: $old_time"
  echo " Neue Systemzeit: $new_time"
  echo "--------------------------------------"

  if command -v timedatectl >/dev/null 2>&1; then
    # NTP deaktivieren, damit die Zeit nicht direkt wieder zurückspringt
    timedatectl set-ntp false
    timedatectl set-time "$new_time"
  else
    date -s "$new_time"
  fi

  echo "Systemzeit wurde aktualisiert."
  sleep 1.5
}

while true; do
  clear
  echo "======================================"
  echo "        Zeitsprung-Menü (Enterprise)"
  echo "======================================"
  echo
  echo "Aktuelle Systemzeit:  $(date '+%Y-%m-%d %H:%M:%S')"
  echo
  echo " 1) +1 Stunde"
  echo " 2) -1 Stunde"
  echo " 3) +5 Stunden"
  echo " 4) -5 Stunden"
  echo " 5) +1 Tag (09:00 Uhr)"
  echo " 6) -1 Tag (09:00 Uhr)"
  echo " 7) +1 Monat (1. des Monats, 09:00 Uhr)"
  echo " 8) -1 Monat (1. des Monats, 09:00 Uhr)"
  echo " q) Beenden"
  echo
  read -rp "Auswahl: " choice

  case "$choice" in
    1)
      new_time=$(date -d "+1 hour" '+%Y-%m-%d %H:%M:%S')
      set_system_time "$new_time"
      ;;
    2)
      new_time=$(date -d "-1 hour" '+%Y-%m-%d %H:%M:%S')
      set_system_time "$new_time"
      ;;
    3)
      new_time=$(date -d "+5 hour" '+%Y-%m-%d %H:%M:%S')
      set_system_time "$new_time"
      ;;
    4)
      new_time=$(date -d "-5 hour" '+%Y-%m-%d %H:%M:%S')
      set_system_time "$new_time"
      ;;
    5)
      # +1 Tag, immer 09:00:00
      target_date=$(date -d "+1 day" '+%Y-%m-%d')
      new_time="${target_date} 09:00:00"
      set_system_time "$new_time"
      ;;
    6)
      # -1 Tag, immer 09:00:00
      target_date=$(date -d "-1 day" '+%Y-%m-%d')
      new_time="${target_date} 09:00:00"
      set_system_time "$new_time"
      ;;
    7)
      # +1 Monat, 1. des nächsten Monats, 09:00:00
      first_next_month=$(date -d "$(date +%Y-%m-01) +1 month" '+%Y-%m-%d')
      new_time="${first_next_month} 09:00:00"
      set_system_time "$new_time"
      ;;
    8)
      # -1 Monat, 1. des vorherigen Monats, 09:00:00
      first_prev_month=$(date -d "$(date +%Y-%m-01) -1 month" '+%Y-%m-%d')
      new_time="${first_prev_month} 09:00:00"
      set_system_time "$new_time"
      ;;
    q|Q)
      echo "Beende Zeitsprung-Menü."
      exit 0
      ;;
    *)
      echo "Ungültige Auswahl."
      sleep 1
      ;;
  esac
done
