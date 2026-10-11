## Neu in DEr Stromtarif 0.3.0

- Bestehenden Home-Assistant-Kalender und eine To-do-Liste beim Einrichten auswählen und später ändern oder deaktivieren.
- Ableseerinnerungen und fällige Abschläge als ganztägige Kalendertermine; Ableseaufgaben in einer To-do-Liste.
- Abschläge unabhängig von Ablesungen planen: Monatstag 1–31, Monatsende, individuelle Termine und Beträge sowie dauerhafte Verschiebe-/Lösch-Ausnahmen.
- Tarife inaktiv setzen oder mit Endzählerstand und optionaler Endabrechnung abschließen. Beim Wechsel bleibt der neue Tarif aktiv; alte Historie und Zahlungen bleiben erhalten.
- Tarifstatus, Zahlungsplan und Endabrechnungen in der Dashboard-Karte und im CSV-Export.
- Erinnerungen werden ohne Duplikate abgeglichen; Störungen externer Ziele werden angezeigt. Fremde Kalendereinträge und Aufgaben bleiben erhalten.

## Aktualisieren

In HACS **v0.3.0** herunterladen und Home Assistant neu starten. Bestehende Tarifbücher werden automatisch erweitert. Falls bisher `main` bzw. eine Commit-ID installiert ist, im Repository-Menü **Erneut herunterladen** und **v0.3.0** wählen.

Bei Verwendung der Karte die Dashboard-Ressource auf `/stromtarif-card.js?v=0.3.0` ändern und Browser aktualisieren.

Kalender und To-do-Liste müssen das Erstellen und Löschen von Einträgen unterstützen. Geplante Abschläge sind keine gebuchten Zahlungen. Der Endtag eines Tarifs bzw. Rechnungszeitraums ist exklusiv.

## Geprüft

29 Python-Tests mit Home Assistant Core 2026.2.3, echten Local-Calendar-/Local-To-do-Komponenten und Chromium-Kartentest bestanden. Die konkrete HA-/HACS-Installation des Nutzers wurde nicht geprüft. Details in `TEST_REPORT.md`.
