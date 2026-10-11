# Verwaltungs-Panel – DEr Stromtarif 0.4.0

Das Verwaltungs-Panel wurde zuerst in einer separaten Testversion umgesetzt und geprüft. Version 0.4.0 veröffentlicht diesen geprüften Stand.

## Bedienung nach Installation von Version 0.4.0

Unter **Einstellungen → Geräte & Dienste → DEr Stromtarif → Konfigurieren → Seitenleiste ein-/ausblenden** die Anzeige aktivieren. Der gemeinsame Eintrag **DEr Stromtarif** erscheint für Administratoren, sobald mindestens ein Tarifbuch die Anzeige aktiviert hat. Die Einstellung ist dauerhaft gespeichert und später änderbar. Auch bei ausgeblendetem Eintrag öffnet **Verwaltung öffnen** in der Dashboard-Karte das Panel und wählt das zugehörige Tarifbuch.

- **Übersicht:** Strompreis je Tarif sowie Verbrauch nach Monat, Quartal oder Jahr, wahlweise für alle oder einen einzelnen Tarif. Effektiver Preis = erfasste Kosten inklusive Grundgebühr / erfasster Verbrauch. Ohne Verbrauch bleibt er unbekannt. Auch ein HA-Sensor und die Karte zeigen den aktuellen effektiven Preis.
- **Ablesungen:** Alle erfassten Ablesungen in einer Tabelle. Datum und Wert einzeln korrigieren; normale Ablesungen entfernen. Anfangsstand und Tarifgrenzen werden mitgeführt und können korrigiert, aber nicht gelöscht werden. Zeitlich oder numerisch widersprüchliche Änderungen werden vollständig verworfen. Ein manuell korrigierter automatischer Eintrag wird zur manuellen Ablesung, damit die Quelle ihn nicht am selben Tag überschreibt.
- **Tarife:** Neue Tarife anlegen, historische Namen und Preise korrigieren, aktuellen Tarif inaktiv setzen, Tarif mit Endstand und optionaler Endabrechnung abschließen. Historische bzw. endgültig abgerechnete Tarife werden nicht reaktiviert. Tarif-Geltungsdaten durch Korrektur der zugehörigen Grenzablesung ändern.
- **Abrechnung & Zahlungen:** Abrechnungsperiode und Monatsplan ändern; einzelne Abschlagstermine planen, verschieben und entfernen; bestätigte Zahlungen einzeln bearbeiten oder entfernen; Endabrechnungen korrigieren oder entfernen. Lieferantenrechnungen bleiben getrennt von berechneten Kosten und Zahlungsbuchungen.
- **Einstellungen:** Seitenleiste, Ableseintervall, Kalender, To-do-Liste, automatische Zählerquelle und Neukalibrierung.
- **CSV:** Vorhandener geschützter Export erreichbar.

## Berechnung und Schutz der Daten

Monats-/Quartals-/Jahresgrenzen ohne Ablesung erfordern eine zeitanteilige Verteilung des Verbrauchs. Diese Werte sind als **Schätzung** gekennzeichnet, die Balken schraffiert. Unvollständige Perioden sind **Teilperioden**; es wird nicht bis zu ihrem Ende hochgerechnet. Kosten und Verbrauch beziehen sich auf die erfassten Vertragszeiträume. Rechnungsgrenzen müssen zunächst in der Endabrechnung korrigiert oder die Rechnung entfernt werden, bevor eine zugehörige Ablesegrenze verschoben wird.

Alle Schreibbefehle erfordern ein Administratorkonto. Jede Änderung verwendet eine Datenrevision. Eine ältere Tabellenansicht kann aktuelle Änderungen oder automatische Zählerstände nicht überschreiben; sie meldet, dass neu geladen werden muss. Speicherung, Sensorwerte, Prognose und Erinnerungen werden nach erfolgreicher Änderung aktualisiert. Kein direktes Bearbeiten der Speicherdateien durch das Panel.

## Prüfung am 11. Oktober 2026

- 38 Python-Tests mit Home Assistant Core 2026.2.3 bestanden.
- Tatsächliche HA-Panelregistrierung mit optionalem Seitentitel, Optionsdialog, Administratorprüfung und Datenrevision geprüft.
- Tatsächliche Backend-Schreibbefehle sowie Äquivalente aller bestehenden Optionsfunktionen geprüft; ungültige Änderungen erhalten die bisherigen Daten.
- Monats-/Quartals-/Jahres-Summen, Schaltjahr, Tarifauswahl, Preis bei Nullverbrauch und synchronisierte Tarifgrenzen geprüft.
- Chromium-Browsertest für Panel bestanden: Tabellenbearbeitung, Fehlerdialog mit erhaltenen Eingaben, Periodenauswahl, Seitenleistenoption, Zielauswahl, CSV-Download, Textmaskierung und schmale Ansicht.
- Bestehender Chromium-Kartentest weiterhin bestanden.
- Python-, JavaScript- und JSON-Dateien geprüft.

Nicht geprüft wurde die konkrete HA-/HACS-Installation des Nutzers. Der Panel-Browsertest verwendet simulierte WebSocket-Antworten; Backend, Panelregistrierung, Speicherung und HA-Komponenten wurden separat im echten Core getestet. Ein vollständig zusammenhängender Browsertest innerhalb der HA-Anwendungsoberfläche steht noch aus.
