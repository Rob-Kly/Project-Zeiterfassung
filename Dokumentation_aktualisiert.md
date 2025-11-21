
# Zeiterfassungssystem – Entwickler- und Administrator-Dokumentation (Aktualisiert)

## 1. Login-Format (NEU)
Das System verwendet nun das Loginformat **Vorname.Nachname**.

- Leerzeichen werden ignoriert
- Groß-/Kleinschreibung spielt keine Rolle
- Beispiel: `Max.Mustermann`

Die Authentifizierung erfolgt serverseitig über:

```
expected_login = f"{first}.{last}"
```

(siehe routes_auth.py)

---

## 2. Änderungen in routes_auth.py
Wesentliche Anpassungen:

- Entfernen der alten „Vorname Nachname“-Logik
- Neue Normalisierung:
  - Eingabe wird lowercase gesetzt
  - Alle Leerzeichen werden entfernt
- Prüfung nur gegen `vorname.nachname`
- Passwortprüfung unverändert
- Session-Verwaltung unverändert

Vorteile:
- Eindeutige Logins, auch bei gleichen Vornamen
- Nutzer werden visuell durch Hinweis in login.html darauf hingewiesen

---

## 3. login.html (Aktualisiert)
Änderungen:

- Statischer Hinweis direkt unter dem Eingabefeld:
  - „Bitte im Format Vorname.Nachname anmelden“
- Keine dynamische JavaScript-Formatprüfung mehr
- Verwendung der CSS-Klasse `.password-hint` anstelle einer zusätzlichen '.login-hint'
- Keine weiteren Styles notwendig

---

## 4. Benutzerverwaltung
Unverändert:

- Benutzerformular nutzt `user_form_macros.html`
- Vorname und Nachname getrennt gespeichert
- Nutzer melden sich dennoch mit `Vorname.Nachname` an
- Admins können weiterhin NFC-Codes zuweisen

Ergänzung:
- In Präsentationen / Schulungen kann erwähnt werden:
  - „Loginname ergibt sich automatisch aus Vorname.Nachname“

---

## 5. Systemkomponenten (Kurzüberblick)
Die folgenden Module bleiben unverändert und funktionieren weiterhin stabil:

- `attendance.py` – Kommen/Gehen, Auto-Korrektur
- `zfa_io.py` – Lesen/Schreiben von Timestamps & userlist
- `worktime_report.py` – Tages-, Wochen-, Monatsberechnungen
- `zfa_passwords.py` – Passwortvalidierungen
- `routes_user.py` – Mitarbeiterbereich
- `routes_admin.py` – Adminbereich inkl. Fehlerzeitenkorrektur
- `nfc_listener.py` – NFC-Leser-Anbindung
- `auto_export.py` – Monatsstartswithzählungen
- `config.py` – Standardwerte und Systemverhalten

---

## 6. Benutzer-/Adminhandbuch (Kurz, aber vollständig)

### Login
- Format: **Vorname.Nachname**
- Beispiel: Max.Mustermann
- Passwort wie vom Admin vergeben oder selbst gesetzt
- Bei temporären Passwörtern → Änderung innerhalb 24h erforderlich

### Mitarbeiterbereich
- Kommen/Gehen per Button oder NFC
- Übersicht: Heute / Woche / Monat
- Heutige Buchungen im Zeitverlauf

### Administratorbereich
- Benutzer anlegen/bearbeiten/löschen
- Rollen ändern (user/admin)
- NFC-Karten zuweisen
- Automatische Buchungen korrigieren
- Monatsreports einsehen

### NFC
- Letzte gescannte Karte wird in `pending_nfc.json` gespeichert
- Admin übernimmt Code per Button auf der Bearbeitungsseite

### Auto-Korrekturen
- Auto-Login 09:00 bei vergessenem Login
- Auto-Logout 18:00 bei vergessenem Logout
- Fehlerkorrekturseite für Admins

---

## 7. Strukturierung / Änderungen im Templates-Ordner
Nur eine einzige Datei wurde angepasst:

- **templates/login.html**

Alle anderen Templates bleiben inhaltlich unverändert.

---

## 8. Empfehlung für Betrieb/Schulung
- Nutzern direkt sagen:
  - „Loginname = Vorname.Nachname“
- Admins sollten wissen:
  - „NFC-Codes werden automatisch zwischengespeichert“
  - „Fehlerzeiten müssen gelegentlich geprüft werden“
  - „Reports sind automatisch pro Monat verfügbar“

---

## 9. Fazit / Nutzen der Änderung
- Deutlich klareres Login-Konzept
- Keine Verwechslungen mehr bei gleichen Vornamen
- UI bleibt minimal und verständlich
- Backend bleibt übersichtlich und stabil
