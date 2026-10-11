# Testbericht – DEr Stromtarif 0.6.0

Geprüft am 11. Oktober 2026 in einer separaten lokalen Testkopie, vor dem Hochladen auf GitHub.

## Ergebnis

- 63 Python-Tests bestanden: 62 Modelltests und ein durchgehender Laufzeittest mit zahlreichen Prüfungen.
- JavaScript-Syntaxprüfung bestanden.
- Chromium-Browsertest der Dashboard-Karte bestanden: Anzeige, Verbrauchs-/Kostentabelle, sichere Textdarstellung und tatsächlicher CSV-Download.
- JSON-Dateien und Python-Dateien geprüft.

## Home Assistant

Testumgebung: **Home Assistant Core 2026.2.3**, CPython 3.13.16. Der vollständige Einrichtungsdialog wurde über den HA-Flow-Manager geöffnet und ein Eintrag erstellt. Alle Sensoren, das Optionsmenü mit dreizehn Dialogen, Zahlungserfassung, automatische Zählerwerte, Ausfallanzeige, dauerhafte Sperre nach Zählerreset und Entladen/Neuladen mit Erhalt der Daten wurden geprüft. Die Tests verwenden echte Home-Assistant-Komponenten. Ausschließlich die lokale Netzwerkadress-Ermittlung ist im Laufzeittest auf Loopback gesetzt, da die Testumgebung keine Netzwerkadapter-Ermittlung erlaubt.

Die ungültige Zahlenfeld-Schrittweite der alten Version ließ sich mit HA Core reproduzieren; `step: any` behebt die Schema-Validierung und erlaubt auch vier oder mehr Nachkommastellen.

## Kalender, To-do und Tarifabschluss

Der Laufzeittest legt zwei echte HA Local Calendar und zwei echte Local To-do Einträge an. Geprüft wurden:

- Kalender/To-do-Auswahl beim ersten Einrichten und in den Optionen.
- Ganztägige Termine mit exklusivem Enddatum am Folgetag.
- Identische Termin-IDs nach wiederholtem Abgleich und aktivem Neuladen.
- Erledigte Ableseaufgabe bleibt erledigt.
- Abschlag verschieben: alter Termin entfällt, neuer Betrag und Datum erscheinen; Intervalländerung verschiebt keinen Abschlag.
- Zielwechsel entfernt eigene künftige Einträge am alten Ziel und erstellt sie am neuen; fremde Termine und Aufgaben bleiben bestehen.
- Inaktivstatus entfernt künftige Erinnerungen, setzt Ablesefälligkeit aus und gibt kein nächstes Ablesedatum aus.
- Neuer Tarif nach Inaktivstatus wird aktiv; Endabrechnung bleibt getrennt von bestätigten Zahlungen.
- Nicht verfügbares Kalenderziel setzt eine Störung; erneuter erfolgreicher Abgleich löscht sie.
- Migration und Reload erhalten alle Daten.

Modelltests prüfen zusätzlich Tag 31, Monatsende, Schaltjahre, individuelle Termine, dauerhafte Ausnahmen, Kollisionsvermeidung, Abrechnungsbeginn ohne Ablesung, Prognose bei Abschluss und vertragsfreie Lücken. Chromium prüft zusätzlich Inaktivstatus, Terminplan, Endabrechnung und Störungsanzeige mit sicherer Textdarstellung.

Der GitHub-Release-Job ist von beiden CI-Testjobs abhängig. Die tatsächliche Veröffentlichung ist separat anhand von GitHub-Tag und Release zu bestätigen.

## Grenzen der Prüfung

Die tatsächliche HA-Installation des Nutzers und dessen konkrete Core-Version sind nicht zugänglich. Ein Sensor wird in der Testinstanz simuliert; reale Zählerhardware wurde nicht angeschlossen. Die Karte wurde mit realem Chromium 140 und simulierten WebSocket-Antworten geprüft, die authentifizierten Backend-Befehle zusätzlich im HA-Laufzeittest. Noch kein kompletter HACS-Download- und Updatevorgang in der Nutzerinstallation getestet.

## Wiederholen

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python -m compileall -q custom_components
npm install --no-save playwright@1.55.0
npx playwright install chromium
node --check custom_components/stromtarif/www/stromtarif-card.js
node tests/test_card.cjs
node tests/test_reading_card.cjs
node --check custom_components/stromtarif/www/stromtarif-panel.js
node tests/test_panel.cjs
```


## Verwaltungs-Panel 0.4.0

Zusätzliche Modellprüfungen für Ablesekorrekturen, synchronisierte Tarifgrenzen, geschützte Rechnungsgrenzen, Löschung normaler Ablesungen, Effektivpreis bei Nullverbrauch, Periodensummen, Tarifauswahl und Schaltjahr.

Im tatsächlichen HA-Core getestet: Panel registrieren, Seitentitel ein-/ausblenden, Optionsdialog, Administratorprüfung, Schreibbefehle mit Datenrevision, atomare Ablehnung ungültiger Werte und Äquivalente aller vorhandenen Optionsfunktionen. Die Backend-Schreibtests verwenden den tatsächlichen WebSocket-Handler und die tatsächliche Speicherung.

Chromium prüft Paneldarstellung, Effektivpreis, Monats-/Quartals-/Jahresauswahl, einzelne Tabellenänderung, Fehlerdialog mit erhaltenen Eingaben, Seitenleistenoption, Zielauswahl, CSV-Download, sichere Textdarstellung und schmale Ansicht. Die WebSocket-Antworten dieses Browsertests sind simuliert. Ein durchgehender Browsertest innerhalb der vollständigen HA-Anwendungsoberfläche ist nicht durchgeführt worden.

## Neue Funktionen 0.5.0

Zusätzliche Modelltests prüfen Zahlungs-Verknüpfungen, idempotente manuelle und automatische Verbuchung, Bearbeiten/Löschen, inaktive Tarife, jährliche Periodenwechsel einschließlich Schaltjahr, Rechnungsüberschneidungen, datierte Abschlagänderungen und individuelle Ausnahmen, Migration von Zählernummern, mehrere physische Wechsel, Tarifwechsel am selben Datum, Kosten- und Verbrauchssummen, CSV sowie Neukalibrierung.

Der echte HA-Laufzeittest prüft zusätzlich stündliche Verarbeitung mit Speicherung und Revision, einmalige Abrechnungsbenachrichtigung, Rechnungsbearbeitung, Abschlagänderungen und Zählerwechsel. Chromium prüft die neuen Panel-Aktionen, Formulare, Zahlungsbearbeitung und CSV; Dashboard-Kartentest weiterhin bestanden.

## Eingabekarte 0.6.0

Chromium-Test der neuen Karte bestanden: Anzeige der Zählernummer, Dezimalwerte, neue Ablesung, Korrektur am selben Datum, Schreibrevision, erhaltene Eingaben bei Fehlern und Aktualisieren, Auswahlwechsel, Sperre inaktiver Tarife und Textmaskierung. Alle 63 Python-Tests und bisherigen Browser-Tests weiterhin bestanden.
