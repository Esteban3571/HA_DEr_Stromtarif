# Testbericht – DEr Stromtarif 0.3.0

Geprüft am 11. Oktober 2026 in einer separaten lokalen Testkopie, vor dem Hochladen auf GitHub.

## Ergebnis

- 29 Python-Tests bestanden: 28 Modelltests und ein durchgehender Laufzeittest mit zahlreichen Prüfungen.
- JavaScript-Syntaxprüfung bestanden.
- Chromium-Browsertest der Dashboard-Karte bestanden: Anzeige, Verbrauchs-/Kostentabelle, sichere Textdarstellung und tatsächlicher CSV-Download.
- JSON-Dateien und Python-Dateien geprüft.

## Home Assistant

Testumgebung: **Home Assistant Core 2026.2.3**, CPython 3.13.16. Der vollständige Einrichtungsdialog wurde über den HA-Flow-Manager geöffnet und ein Eintrag erstellt. Alle Sensoren, das Optionsmenü mit zwölf Dialogen, Zahlungserfassung, automatische Zählerwerte, Ausfallanzeige, dauerhafte Sperre nach Zählerreset und Entladen/Neuladen mit Erhalt der Daten wurden geprüft. Die Tests verwenden echte Home-Assistant-Komponenten. Ausschließlich die lokale Netzwerkadress-Ermittlung ist im Laufzeittest auf Loopback gesetzt, da die Testumgebung keine Netzwerkadapter-Ermittlung erlaubt.

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
```
