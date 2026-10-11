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
