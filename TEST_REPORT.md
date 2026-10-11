# Testbericht – DEr Stromtarif 0.2.0

Geprüft am 11. Oktober 2026 in einer separaten lokalen Testkopie, vor dem Hochladen auf GitHub.

## Ergebnis

- 21 Python-Tests bestanden: 20 Modelltests und ein durchgehender Laufzeittest mit zahlreichen Prüfungen.
- JavaScript-Syntaxprüfung bestanden.
- Chromium-Browsertest der Dashboard-Karte bestanden: Anzeige, Verbrauchs-/Kostentabelle, sichere Textdarstellung und tatsächlicher CSV-Download.
- JSON-Dateien und Python-Dateien geprüft.

## Home Assistant

Testumgebung: **Home Assistant Core 2026.2.3**, CPython 3.13.16. Der vollständige Einrichtungsdialog wurde über den HA-Flow-Manager geöffnet und ein Eintrag erstellt. Alle Sensoren, das Optionsmenü mit acht Dialogen, Zahlungserfassung, automatische Zählerwerte, Ausfallanzeige, dauerhafte Sperre nach Zählerreset und Entladen/Neuladen mit Erhalt der Daten wurden geprüft. Die Tests verwenden echte Home-Assistant-Komponenten. Ausschließlich die lokale Netzwerkadress-Ermittlung ist im Laufzeittest auf Loopback gesetzt, da die Testumgebung keine Netzwerkadapter-Ermittlung erlaubt.

Die ungültige Zahlenfeld-Schrittweite der alten Version ließ sich mit HA Core reproduzieren; `step: any` behebt die Schema-Validierung und erlaubt auch vier oder mehr Nachkommastellen.

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
