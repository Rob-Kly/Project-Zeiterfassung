"""
Zentrale Konfigurationsdatei für das Zeiterfassungssystem.

Hier stehen alle globalen Einstellungen, die von mehreren Modulen genutzt werden.
"""

# ==========================================================
# ZEITERFASSUNG – STANDARDWERTE
# ==========================================================
# Standardarbeitszeit: 09:00–18:00 Uhr
# DEFAULT_LATE_LOGIN: Uhrzeitgrenze, ab der ein vergessener Login
# am Morgen angenommen und automatisch korrigiert wird.
DEFAULT_WORK_START = (9, 0, 0)    # 09:00 Uhr
DEFAULT_WORK_END   = (18, 0, 0)   # 18:00 Uhr
DEFAULT_LATE_LOGIN = 15           # 15:00 Uhr


# ==========================================================
# SYSTEMVERHALTEN
# ==========================================================
SESSION_TIMEOUT = 300             # Sekunden (Inaktivität = 5 Minuten)
PASSWORD_CHANGE_GRACE_HOURS = 24  # Temporäres Passwort gültig für 24h


# ==========================================================
# REPORTING
# ==========================================================
REPORTS_DIR = "reports"


# ==========================================================
# NFC
# ==========================================================
DEBOUNCE_SECONDS = 2              # Sekunden Schutz vor Mehrfach-Triggern
