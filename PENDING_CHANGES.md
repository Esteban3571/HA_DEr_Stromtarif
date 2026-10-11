# Teststand: historische Daten und getrennte Abrechnung

Noch kein neues Release. Änderungen im Testzweig sammeln; Veröffentlichung erst auf ausdrücklichen Auftrag.

- Neue Ansicht **Historische Daten** mit getrennten Schritten für Ablesungen/Zähler, Tarife, Rechnungen und Vorschau.
- Neue und historische Tarife ohne Rechnungsfelder anlegen; Tarifwechsel erstellt auch im Backend keine Rechnung. Bestehende Rechnungen bleiben erhalten. Periodenrechnungen separat unter **Abrechnung & Zahlungen** erfassen.
- Rechnungen haben eigene Zeiträume und dürfen mehrere Tarife/Zähler umfassen; Rechnung ist für eine Tarifnacherfassung nicht erforderlich.
- Unvollständige Entwürfe speichern, Nachbardaten und konkrete Grenzdatumvorschläge anzeigen, Überschneidungen prüfen.
- Inklusive Enddaten im Assistenten; intern weiterhin exklusive Grenzen.
- Lücken/unbekannte Preise bleiben ausdrücklich unbekannt; Kosten und darauf beruhende Prognosen nicht als null ausgeben. Verbrauch bleibt berechenbar.
- Grenzstände nur nach ausdrücklicher Auswahl zwischen bekannten Ständen interpolieren, als geschätzt markieren; keine Extrapolation.
- Übernahme erst nach fehlerfreier Vorschau und Bestätigung, Revision und Prüfung auf zwischenzeitlich geänderte Historie. Vorheriger Stand wiederherstellbar; Zahlungen bleiben erhalten. Automatische Zählerquelle nach Übernahme/Wiederherstellung neu kalibrieren.

## Prüfung am 11. Oktober 2026

72 Python-Tests bestanden, einschließlich echtem Laufzeittest mit Home Assistant Core 2026.2.3 und Administrator-/WebSocket-Prüfungen. Drei Chromium-Testprogramme bestanden (Panel mit simuliertem WebSocket-Backend, bestehende Karte, Eingabekarte). Neue Fälle prüfen unabhängige Rechnungszeiträume, fehlende Rechnungen, unvollständige Entwürfe, unbekannte Kosten, Schätzungen, Konflikte, veraltete Entwürfe und Wiederherstellung.

Die aktuelle Home-Assistant-Version und die konkrete Nutzerinstallation wurden nicht geprüft. Hauptzweig, Versionsnummer und bestehendes Release 0.6.0 bleiben unverändert.

## Dashboard-Karten: Auffindbarkeit

Release 0.6.0 enthält beide Karten im ausgelieferten JavaScript. Der bisherige Stand lädt die Dashboard-Ressource jedoch nur bei manuellem Eintrag; die Integration selbst registriert lediglich die URL als statischen Pfad.

Im Teststand wird das Kartenmodul nun über Home Assistants Frontend automatisch geladen, auch wenn das Frontend erst später startet. Ein Fingerabdruck des ausgelieferten Skripts in der URL vermeidet eine veraltete Ressource nach Updates. Beide Karten haben eine Standardkonfiguration für die Kartenauswahl. Mehrfaches Laden (bestehende manuelle Ressource plus automatischer Eintrag) erzeugt keine doppelten Karteneinträge oder Custom-Element-Registrierungen.

Erneut 72 Python-Tests und drei Chromium-Programme bestanden. Der HA-Laufzeittest prüft den tatsächlichen Eintrag im Frontend-Modulmanager; Chromium prüft doppelte Skriptausführung und Kartenauswahl-Metadaten. Der Kartenpicker von Home Assistant selbst und die konkrete Nutzerinstallation wurden nicht getestet.

Für bereits installiertes 0.6.0 weiterhin `/stromtarif-card.js?v=0.6.0` als JavaScript-Modul unter Dashboard-Ressourcen eintragen bzw. vorhandenen Eintrag aktualisieren, Browser neu laden und `custom:stromtarif-reading-card` hinzufügen. Die Korrektur bleibt im Testzweig, kein Release wurde erstellt.
