## Neu in DEr Stromtarif 0.4.0

- **Verwaltungs-Panel:** Optionaler Eintrag „DEr Stromtarif“ links in der Home-Assistant-Seitenleiste. Auch über „Verwaltung öffnen“ in der Dashboard-Karte erreichbar.
- **Ablesetabelle:** Jede erfasste Ablesung einzeln mit Datum und Zählerstand korrigieren; Verbrauch und Kosten werden neu berechnet. Ungültige Änderungen werden ohne Datenverlust abgewiesen.
- **Alle Einstellungen im Panel:** Tarife, Preise, Aktivstatus, Abschluss, Abschläge, Zahlungen, Endabrechnungen, Ableseintervall, Kalender, To-do-Liste und Zählerquelle.
- **Strompreis je Tarif:** Erfasste Kosten inklusive anteiliger Grundgebühr geteilt durch erfassten Verbrauch; zusätzlicher Sensor und Anzeige in der Karte.
- **Verbrauchsansicht:** Monat, Quartal oder Jahr wählen und nach Tarif filtern. Geschätzte Werte und unvollständige Perioden sind gekennzeichnet.
- **Geschütztes Speichern:** Nur Administratoren; eine veraltete Tabellenansicht kann parallele Änderungen nicht überschreiben.

## Aktualisieren und öffnen

1. In HACS **v0.4.0** herunterladen und Home Assistant neu starten.
2. Unter **Einstellungen → Geräte & Dienste → DEr Stromtarif → Konfigurieren → Seitenleiste ein-/ausblenden** den Eintrag aktivieren.
3. Falls die Karte verwendet wird, ihre Ressource auf `/stromtarif-card.js?v=0.4.0` ändern und Browser aktualisieren.

Bestehende Tarifbücher bleiben erhalten. Das Panel benötigt ein Administratorkonto. Anfangsstände und Tarifgrenzen können korrigiert, aber nicht gelöscht werden; Datumsgrenzen einer Endabrechnung zuerst in der Rechnung korrigieren. Ohne erfassten Verbrauch ist kein effektiver Preis berechenbar.

## Geprüft

38 Python-Tests mit Home Assistant Core 2026.2.3 sowie Chromium-Panel- und Kartentests. Die konkrete HA-/HACS-Installation des Nutzers wurde nicht geprüft. Details in `TEST_REPORT.md` und `PANEL.md`.
