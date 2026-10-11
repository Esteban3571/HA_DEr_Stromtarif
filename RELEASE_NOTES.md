# Versionshinweise

Neueste Version zuerst. Ab 0.3.0 als GitHub-Releases; ältere Versionsstände wurden über den Hauptzweig bereitgestellt.

## 0.5.0

- **Abschläge bezahlen:** Geplanten Abschlag mit einem Klick als bezahlt markieren; Datum und Betrag anschließend unter „Bezahlte Abschläge“ ändern. Doppelte Buchungen desselben Termins werden verhindert.
- **Optionale Automatik:** Einzelne Abschläge am Fälligkeitstag automatisch im Tarifbuch verbuchen. Keine Überweisung oder Bankanbindung. Verarbeitung beim Start und stündlich; bereits fällige aktivierte Termine werden nachgetragen. Nach dem Löschen einer Zahlung wird ihre Automatik ausgeschaltet.
- **Abschlagänderungen ab Datum:** Mehrere Beträge mit „Gültig ab“ planen, korrigieren und entfernen; auch zum Beginn der nächsten Rechnungsperiode. Tatsächliche Zahlungen und individuelle Termin-Ausnahmen bleiben erhalten.
- **Jährliche Periodenabrechnung:** Frei wählbarer Stichtag, Fälligkeitshinweis und bearbeitbare Lieferantenrechnung mit Nachzahlung oder Guthaben. Optional nächste Jahresperiode beginnen; der Tarif bleibt aktiv.
- **Zählernummern und Austausch:** Nummer je Ablesung, Korrektur vorhandener Nummern und Zählerwechsel mit altem Endstand und neuem Anfangsstand. Verbrauch und Kosten werden über alle Zähler summiert; Tarif und Rechnungsperiode laufen weiter.
- **Geordnete Dokumentation:** README, Release Notes und Changelog mit neuester Version zuerst. Jedes Release verwendet ausschließlich seinen eigenen Versionsabschnitt.

### Aktualisieren und bedienen

1. In HACS **v0.5.0** herunterladen und Home Assistant neu starten.
2. Die Dashboard-Ressource gegebenenfalls auf `/stromtarif-card.js?v=0.5.0` ändern und Browser neu laden.
3. Im Panel unter **Ablesungen → Zählernummern** die Nummer des bisherigen Zählers nachtragen. Alte Daten bleiben erhalten; unbekannte Nummern werden nicht erfunden.
4. Unter **Abrechnung & Zahlungen** geplante Zahlungen bestätigen, datierte Abschlagänderungen und Periodenabrechnungen erfassen. Die Automatik je Termin unter **Ändern / entfernen** einschalten.

Stichtage sind exklusive Enddaten: Eine Periode bis 1. Januar endet mit dem 31. Dezember. Wechsel werden chronologisch ab der letzten Ablesung erfasst; nachträgliches Einfügen eines Wechsels vor bereits erfasste Folgestände ist nicht unterstützt. Nach einem Zählerwechsel die automatische Zählerquelle neu auswählen und kalibrieren. Historische manuelle Zahlungen ohne Plan-Verknüpfung werden nicht automatisch zugeordnet; vor Aktivierung alter Automatiktermine bestehende Zahlungen prüfen.

### Geprüft

63 Python-Tests mit Home Assistant Core 2026.2.3 sowie Chromium-Panel- und Kartentests bestanden. Die konkrete HA-/HACS-Installation des Nutzers wurde nicht geprüft. Details in [TEST_REPORT.md](TEST_REPORT.md) und [PANEL.md](PANEL.md).

## 0.4.0

- **Verwaltungs-Panel:** Optionaler Eintrag „DEr Stromtarif“ links in der Home-Assistant-Seitenleiste. Auch über „Verwaltung öffnen“ in der Dashboard-Karte erreichbar.
- **Ablesetabelle:** Jede erfasste Ablesung einzeln mit Datum und Zählerstand korrigieren; Verbrauch und Kosten werden neu berechnet. Ungültige Änderungen werden ohne Datenverlust abgewiesen.
- **Alle Einstellungen im Panel:** Tarife, Preise, Aktivstatus, Abschluss, Abschläge, Zahlungen, Endabrechnungen, Ableseintervall, Kalender, To-do-Liste und Zählerquelle.
- **Strompreis je Tarif:** Erfasste Kosten inklusive anteiliger Grundgebühr geteilt durch erfassten Verbrauch; zusätzlicher Sensor und Anzeige in der Karte.
- **Verbrauchsansicht:** Monat, Quartal oder Jahr wählen und nach Tarif filtern. Geschätzte Werte und unvollständige Perioden sind gekennzeichnet.
- **Geschütztes Speichern:** Nur Administratoren; eine veraltete Tabellenansicht kann parallele Änderungen nicht überschreiben.

### Aktualisieren und öffnen

1. In HACS **v0.4.0** herunterladen und Home Assistant neu starten.
2. Unter **Einstellungen → Geräte & Dienste → DEr Stromtarif → Konfigurieren → Seitenleiste ein-/ausblenden** den Eintrag aktivieren.
3. Falls die Karte verwendet wird, ihre Ressource auf `/stromtarif-card.js?v=0.4.0` ändern und Browser aktualisieren.

Bestehende Tarifbücher bleiben erhalten. Das Panel benötigt ein Administratorkonto. Anfangsstände und Tarifgrenzen können korrigiert, aber nicht gelöscht werden; Datumsgrenzen einer Endabrechnung zuerst in der Rechnung korrigieren. Ohne erfassten Verbrauch ist kein effektiver Preis berechenbar.

### Geprüft

38 Python-Tests mit Home Assistant Core 2026.2.3 sowie Chromium-Panel- und Kartentests. Die konkrete HA-/HACS-Installation des Nutzers wurde nicht geprüft. Details in `TEST_REPORT.md` und `PANEL.md`.

## 0.3.0

- Bestehenden Home-Assistant-Kalender und eine To-do-Liste beim Einrichten auswählen und später ändern oder deaktivieren.
- Ableseerinnerungen und fällige Abschläge als ganztägige Kalendertermine; Ableseaufgaben in einer To-do-Liste.
- Abschläge unabhängig von Ablesungen planen: Monatstag 1–31, Monatsende, individuelle Termine und Beträge sowie dauerhafte Verschiebe-/Lösch-Ausnahmen.
- Tarife inaktiv setzen oder mit Endzählerstand und optionaler Endabrechnung abschließen. Beim Wechsel bleibt der neue Tarif aktiv; alte Historie und Zahlungen bleiben erhalten.
- Tarifstatus, Zahlungsplan und Endabrechnungen in der Dashboard-Karte und im CSV-Export.
- Erinnerungen werden ohne Duplikate abgeglichen; Störungen externer Ziele werden angezeigt. Fremde Kalendereinträge und Aufgaben bleiben erhalten.

### Aktualisieren

In HACS **v0.3.0** herunterladen und Home Assistant neu starten. Bestehende Tarifbücher werden automatisch erweitert. Falls bisher `main` bzw. eine Commit-ID installiert ist, im Repository-Menü **Erneut herunterladen** und **v0.3.0** wählen.

Bei Verwendung der Karte die Dashboard-Ressource auf `/stromtarif-card.js?v=0.3.0` ändern und Browser aktualisieren.

Kalender und To-do-Liste müssen das Erstellen und Löschen von Einträgen unterstützen. Geplante Abschläge sind keine gebuchten Zahlungen. Der Endtag eines Tarifs bzw. Rechnungszeitraums ist exklusiv.

### Geprüft

29 Python-Tests mit Home Assistant Core 2026.2.3, echten Local-Calendar-/Local-To-do-Komponenten und Chromium-Kartentest bestanden. Die konkrete HA-/HACS-Installation des Nutzers wurde nicht geprüft. Details in `TEST_REPORT.md`.

## 0.2.0

- Einrichtungsfehler durch ungültige Schrittweite des Zahlen-Selektors behoben.
- Abrechnungsperiode, monatlichen Abschlagsplan und tatsächlich bezahlte Abschläge getrennt erfassen.
- Kosten-/Saldo-Prognose mit Kennzeichnung von Schätzungen und Abgrenzung geplanter Zahlungen.
- Dashboard-Karte mit Tarif-, Ablese-, Verbrauchs-, Kosten- und Zahlungshistorie; CSV-Download.
- Authentifizierte, auf Administratoren beschränkte Historien- und Exportbefehle.
- Kumulativen Wh-/kWh-Sensor kalibrieren und automatisch übernehmen; manuelle Erfassung bleibt möglich.
- Ausfälle und Resets erkennen; nach erkanntem Reset bis zur Neukalibrierung pausieren.
- Bestehende Tarifbücher beim Laden ohne Verlust der Historie erweitern.
- Home-Assistant-Laufzeit- und Chromium-Kartentests für den Testworkflow ergänzt.

## 0.1.1

- Anzeigename auf DEr Stromtarif geändert.
- HACS- und Home-Assistant-Einrichtungsbuttons in der Anleitung ergänzt.

## 0.1.0

- Feste Stromtarife, manuelle Ablesungen, kalendergenaue Grundgebühr und Ableseerinnerung.
