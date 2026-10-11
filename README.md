# DEr Stromtarif für Home Assistant

Version 0.4.0 – lokale HACS Custom Integration, keine separate App / kein Docker-Add-on.

Verwaltet feste Stromtarife, manuelle Zählerstände, Tarifwechsel und Ableseerinnerungen. Alle Daten bleiben in Home Assistant. Mehrere Zähler können als separate Integrationseinträge angelegt werden.

## Installation mit HACS

[![In HACS installieren](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Esteban3571&repository=HA_DEr_Stromtarif&category=integration)

**1. Installieren:** Der Button öffnet das Repository in HACS deiner Home-Assistant-Installation. HACS muss bereits eingerichtet sein. Repository bei Bedarf hinzufügen, herunterladen und Home Assistant neu starten.

[![In Home Assistant einrichten](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=stromtarif)

**2. Einrichten:** Nach dem Download und Neustart öffnet dieser Button die Einrichtung von **DEr Stromtarif**. Beim ersten Aufruf gegebenenfalls die Adresse deiner Home-Assistant-Installation in My Home Assistant hinterlegen.

### Alternativ manuell

1. HACS öffnen → Menü → **Benutzerdefinierte Repositories**.
2. `https://github.com/Esteban3571/HA_DEr_Stromtarif` als Kategorie **Integration** hinzufügen.
3. **DEr Stromtarif** herunterladen und Home Assistant neu starten.
4. Einstellungen → Geräte & Dienste → Integration hinzufügen → **DEr Stromtarif**.
5. Tarifname, Startdatum, Anfangszählerstand, Arbeitspreis, monatliche Grundgebühr und Erinnerungsintervall eingeben.

Benötigt Home Assistant **2025.12 oder neuer**. Alternativ `custom_components/stromtarif` nach `/config/custom_components/stromtarif` kopieren und neu starten.

## Bedienung

Unter Einstellungen → Geräte & Dienste → DEr Stromtarif → **Konfigurieren**:

- **Ablesung erfassen:** kumulativen Zählerstand in kWh und tatsächliches Ablesedatum eingeben. Standardintervall: 90 Tage ab letzter Ablesung, keine festen Quartalstermine.
- **Neuen Tarif hinterlegen:** ersten Geltungstag, Anfangszählerstand und neue Preise erfassen. Dieser Stand schließt den bisherigen Tarif ab; die alte Historie bleibt erhalten. Am gleichen Tag wie die letzte Ablesung muss der Stand identisch sein.
- **Ableseintervall ändern:** 1 bis 730 Tage. Änderung wirkt ab letzter Ablesung.
- **Letzte Ablesung korrigieren:** letzte normale Ablesung entfernen und korrekt neu erfassen. Anfangsstand und Tarifgrenzen sind geschützt.

Der Arbeitspreis wird in **EUR/kWh** eingegeben: 30 Cent = **0,30 EUR/kWh**. Grundgebühr monatlich in Euro, inklusive Steuern. Einen Jahresgrundpreis vorher durch 12 teilen. Zählerstände dürfen gleich bleiben, aber nicht sinken. Zählerwechsel / Überlauf sind in dieser Version nicht unterstützt. Nur bereits eingetretene Daten, keine zukünftigen Tarife.

## Kosten und Historie

Verbrauch = Differenz der Zählerstände. Jede Differenz wird mit dem im jeweiligen Zeitraum gültigen Tarif berechnet. Ein Tarifwechsel benötigt daher zwingend eine Ablesung an der Tarifgrenze.

Die Grundgebühr wird kalendergenau anteilig berechnet: monatliche Gebühr × erfasste Tage / Tage des betreffenden Monats. Das Anfangsdatum ist eingeschlossen, das Enddatum ausgeschlossen. Beispiel: 1. Januar bis 1. April, 600 kWh × 0,30 EUR + 3 × 12 EUR = **216 EUR**. Lieferanten können andere Tageskonventionen verwenden; die Berechnung ist keine verbindliche Rechnung.

Die Sensoren „… erfasst“ enthalten nur Kosten **bis zur letzten Ablesung**. Unbekannter Verbrauch danach wird nicht geschätzt. „Grundgebühr seit letzter Ablesung“ zeigt separat die inzwischen angefallene Grundgebühr. Beim Gesamtkostensensor stehen Tarif- und Ablesehistorie als Attribute zur Verfügung. Kein separater eigener Webbildschirm nötig.

## Erinnerung

Ein Fälligkeits-Binärsensor und das Datum „Nächste Ablesung“ stehen bereit. Bei Fälligkeit erzeugt die Integration einmal eine dauerhafte Home-Assistant-Benachrichtigung. Prüfung beim Start und danach stündlich, daher bis zu einer Stunde Verzögerung. Die letzte Ablesung startet das Intervall neu. Smartphone-Push kann über eine Automation auf den Fälligkeits-Binärsensor ergänzt werden.

## Speicherung / Grenzen

Tarife und Ablesungen werden separat in Home Assistants `.storage` dauerhaft gespeichert; Neustarts und Updates erhalten sie. Home-Assistant-Backups sichern diese Daten. **Das Entfernen des Integrationseintrags löscht dessen Tarifbuch.** Die UI-Optionen enthalten nicht die Historie.

Manuelle Ablesungen werden bewusst nicht als zeitgenaue Statistik ins Energie-Dashboard eingespeist: ein Quartalsverbrauch würde sonst dem Eingabezeitpunkt zugeordnet. Diese Version bietet Kosten- und Verbrauchssensoren für normale Dashboards. Rückwirkende Tarifkorrekturen sind noch nicht implementiert.

## Entwicklungsstand und Tests

Erste Version: vor produktiver Nutzung mit einem Testeintrag prüfen. Berechnungen und Einrichtung werden in einer isolierten Home-Assistant-Core-Testumgebung geprüft. Die Version auf deiner eigenen Installation muss nach dem Update ebenfalls geprüft werden.

```sh
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

Fehler und Erweiterungswünsche: https://github.com/Esteban3571/HA_DEr_Stromtarif/issues

Lizenz: MIT.



## Neu in 0.2.0

Die ungültige Zahlenfeld-Schrittweite, die den Einrichtungsdialog verhindern konnte, wurde korrigiert. Der interne Domainname und die IDs bleiben gleich; bestehende Daten werden beim Laden um neue Felder ergänzt.

### Abschläge, Abrechnung und Prognose

Unter **Konfigurieren → Abrechnung und Abschlag** Beginn, exklusives Enddatum, monatlichen Abschlag und Zahlungstag wählen. Der Beginn kann unabhängig von Ablesedaten gewählt werden; er darf nicht vor dem ersten Eintrag des Tarifbuchs liegen. Standard ist das erste Ablesedatum bis zum gleichen Datum im Folgejahr.

**Zahlung erfassen** bucht tatsächlich bezahlte Beträge; der monatliche Plan bucht keine Zahlungen automatisch. **Letzte Zahlung entfernen** korrigiert die zuletzt eingegebene Zahlung. Alle Zahlungen bleiben in der Historie. Im Zeitraum werden nur Zahlungen mit Datum ab Beginn und vor Ende gezählt.

Sensoren zeigen Periodenkosten, bezahlte und geplante Abschläge, bisherigen Saldo und Kosten-/Saldoprognose. Positiver Saldo = Nachzahlung, negativer = Guthaben. Die Prognose extrapoliert den bisherigen Tagesverbrauch mit dem aktuellen Arbeitspreis und zukünftiger kalendergenauer Grundgebühr. Sie berücksichtigt keine Saisonalität, Preisänderungen in der Zukunft oder Boni. Ohne Verbrauchszeitraum bleibt sie unbekannt. Liegt eine Ablesung über dem Periodenende, wird der Grenzverbrauch linear nach Tagen geschätzt und gekennzeichnet.

### Dashboard-Karte und CSV

1. In den Dashboard-Einstellungen unter **Ressourcen** `/stromtarif-card.js?v=0.4.0` als **JavaScript-Modul** hinzufügen (gegebenenfalls erweiterten Modus im Benutzerprofil aktivieren).
2. Eine manuelle Karte hinzufügen:

```yaml
type: custom:stromtarif-card
```

Die Karte zeigt Tarif, Ablesungen, Fälligkeit, Abschläge, Prognose und Tabellen der gesamten Historie. Bei mehreren Tarifbüchern gibt es eine Auswahl. Optional kann `entry_id` in der Kartenkonfiguration eine Auswahl vorgeben. Aktualisierung alle 30 Sekunden oder per Button. Die Karte benötigt ein **Administratorkonto**; ihre WebSocket-Schnittstellen prüfen diese Berechtigung.

**Historie als CSV herunterladen** exportiert Tarife, Ablesungen und bestätigte Zahlungen direkt im Browser, mit Semikolon-Trennung und UTF-8. Kein öffentlicher Datenexport, keine Dateien mit Tarifdaten unter `/local`. CSV-Textfelder sind gegen Tabellenformeln abgesichert.

### Automatischer Zählersensor

Zuerst eine aktuelle manuelle Ablesung erfassen. Dann unter **Automatischen Zählersensor wählen** einen Sensor aktivieren. Unterstützt werden kumulative Energiesensoren mit `device_class: energy`, `state_class: total` oder `total_increasing` und Einheit **kWh** oder **Wh**. Ein W-Leistungssensor oder zurücksetzender Tagesverbrauch eignet sich nicht.

Der Sensor wird beim Aktivieren auf den letzten manuellen Stand kalibriert. Ab dem folgenden Kalendertag entstehen automatisch Ablesungen; ein automatischer Tagesstand wird im Tagesverlauf aktualisiert. Änderungen der Sensorentität werden sofort verarbeitet, zusätzlich wird stündlich und beim Neustart geprüft. Datum entspricht dem Tag der Übernahme, nicht einem nachträglich behaupteten Messzeitpunkt.

Bei `unknown`, `unavailable`, sinkendem Rohwert oder einer Abweichung hinter den manuellen Stand pausiert die Übernahme und **Zählersensor gestört** zeigt den Fehler. Werte werden nicht auf null gesetzt. Manuelle Erfassung bleibt möglich. Nach einem Reset: aktuellen Stand erfassen und die Quelle erneut auswählen, um neu zu kalibrieren. Fehlende Daten während Ausfällen sind nur bei einem weiterhin kumulativen Sensor beim Wiederkehren nachholbar. Tarifwechsel benötigen weiterhin einen expliziten Grenzzählerstand.

### Testworkflow

Änderungen entstehen zuerst in einer separaten lokalen Testkopie. Erst nach bestandenen Prüfungen werden sie auf den Hauptzweig übertragen. Tests der HA-Oberfläche und Laufzeit stehen in `tests/test_runtime.py`; reine Berechnungen in `tests/test_model.py` und `tests/test_features.py`.

Testdetails: [TEST_REPORT.md](TEST_REPORT.md). Versionshistorie: [CHANGELOG.md](CHANGELOG.md).


## Neu in 0.3.0

### Kalender und Aufgaben

Beim Einrichten oder Tarifwechsel optional einen bestehenden HA-Kalender und eine To-do-Liste auswählen. Unter **Konfigurieren → Kalender und To-do-Liste ändern** lassen sich die Ziele später wechseln oder durch Leeren der Felder deaktivieren. Es werden nur Ziele angeboten, die Einträge **erstellen und löschen** können, zum Beispiel Local Calendar und Local To-do. Einen Kalender bei Bedarf zuerst in Home Assistant anlegen.

Der Kalender erhält die nächste Ablesung und geplante Abschläge als **ganztägige Termine** mit exklusivem Enddatum am Folgetag. Ablesungen und Abschläge sind einzeln zuschaltbar. In der To-do-Liste entsteht eine Ableseaufgabe, bei entsprechender Unterstützung mit Fälligkeitsdatum. Erledigte Aufgaben bleiben erledigt; die nächste Ablesung erzeugt eine neue Aufgabe. Termine buchen keine Zahlungen.

Die Integration markiert eigene Einträge und gleicht sie nach Änderungen, beim Start und stündlich ab. Neustarts erzeugen keine Duplikate. Bei Zielwechsel werden eigene offene Aufgaben und zukünftige Termine am alten Ziel entfernt; vergangene Abschlagstermine bleiben als Historie erhalten. Fremde Einträge bleiben bestehen. Ein nicht verfügbares Ziel zeigt **Erinnerungsziel gestört** und den Fehler in der Karte; das Tarifbuch bleibt bedienbar. Der Abgleich wird automatisch erneut versucht.

### Flexible Abschläge

Unter **Abrechnung und Abschlag** Monatstag **1–31** wählen; **0 = Monatsende**. Existiert ein Tag nicht, fällt er auf den letzten Tag des Monats, einschließlich 29. Februar in Schaltjahren. Es erfolgt keine automatische Verschiebung wegen Wochenenden oder Feiertagen.

Unter **Einzelnen Abschlag planen, verschieben oder entfernen** eigene Termine und Beträge erfassen. Zum Verschieben dient das ursprüngliche Datum als Kennung; zum Entfernen den entsprechenden Schalter aktivieren. Diese Ausnahmen bleiben bei Änderungen des monatlichen Plans bestehen. Für einen vollständig individuellen Plan den Modus **Nur einzelne Termine** auswählen. Die Karte zeigt Termin, Betrag und ursprüngliches Datum. Pro Datum wird nur ein geplanter Abschlag berücksichtigt; Ausnahmen haben Vorrang vor einer später auf dasselbe Datum fallenden monatlichen Zahlung.

Zahlungsplan und Ableseintervall sind unabhängig. Eine Ablesung verschiebt keine Zahlung. Abrechnungsbeginn benötigt keine Ablesung am selben Tag; zeitanteilige Verbrauchsgrenzen werden als Schätzung gekennzeichnet. Kalender und Prognose verwenden denselben Zahlungsplan. Bezahlte Abschläge weiterhin separat unter **Zahlung erfassen** buchen.

### Inaktive Tarife und Endabrechnung

**Aktuellen Tarif inaktiv setzen** beendet Erinnerungen und automatische Ablesungen ohne Rechnung; die letzte erfasste Ablesung ist die Abschlussgrenze. Für einen genauen Abschluss **Tarif abschließen** mit Enddatum und Endzählerstand verwenden. Enddatum bedeutet erster Tag ohne diesen Vertrag (exklusiv).

Optional eine **Endabrechnung** mit Rechnungsbeginn, tatsächlichem Rechnungsbetrag und ausgewiesener Nachzahlung oder Guthaben erfassen. Diese Lieferantenrechnung bleibt getrennt von den berechneten Kosten und bestätigten Zahlungen und ist in Karte und CSV sichtbar. Der Rechnungsbetrag wird nicht erneut als Zahlung gebucht. Beim Tarifwechsel kann die Rechnung des alten Tarifs direkt erfasst werden; der alte Tarif wird inaktiv und der neue aktiv. Zeit zwischen einem abgeschlossenen Vertrag und einem späteren Tarifstart wird nicht dem alten Tarif berechnet. Bestehende Daten werden automatisch ergänzt, historische Tarife als inaktiv markiert.

### Lesbare Updates

Versionen werden als benannte GitHub-Releases mit Semver-Tag und kurzen deutschen Versionshinweisen veröffentlicht. Der Release-Workflow startet nach einem Push auf `main` und veröffentlicht erst nach erfolgreichen Modell-, HA-Laufzeit- und Kartentests. Er überschreibt kein bestehendes Release.

Falls HACS bisher `main` oder eine kurze Commit-ID anzeigt: Repository öffnen → Menü → **Erneut herunterladen**, Version **v0.3.0** auswählen, herunterladen und Home Assistant neu starten. Je nach HACS-Version kann die Menübezeichnung abweichen. Für die Dashboard-Karte die Ressource auf `/stromtarif-card.js?v=0.4.0` ändern und Browser aktualisieren. HACS-Installation und Darstellung in deiner eigenen Instanz wurden hier nicht getestet.


## Neu in 0.4.0: Verwaltungs-Panel

Unter **Konfigurieren → Seitenleiste ein-/ausblenden** den optionalen Eintrag **DEr Stromtarif** aktivieren. Er ist für Administratoren sichtbar. Auch ohne Seitenleisten-Eintrag öffnet **Verwaltung öffnen** in der Karte die Oberfläche für das ausgewählte Tarifbuch.

- Alle Ablesungen als Tabelle, Datum und Zählerstand einzeln korrigieren. Verbrauch, Kosten und Prognose werden neu berechnet. Widersprüchliche Änderungen werden vollständig verworfen.
- Alle bisherigen Optionen im Panel: Tarifwechsel, historische Tarifpreise, Aktivstatus, Abschluss, Abschlagsplan, Zahlungen, Endabrechnungen, Kalender, To-do-Liste, Ableseintervall und automatische Zählerquelle.
- Effektiver Strompreis je Tarif inklusive anteiliger Grundgebühr; zusätzlicher Sensor und Anzeige in der Karte. Ohne Verbrauch bleibt der Preis unbekannt.
- Verbrauch nach **Monat, Quartal oder Jahr**, für alle Tarife oder einen einzelnen Tarif. Zeitanteilig verteilte Werte als Schätzung, unvollständige Perioden als Teilperiode gekennzeichnet.
- Datenrevision verhindert, dass eine alte Tabellenansicht inzwischen geänderte Zählerstände überschreibt.

Bedienung und Grenzen: [PANEL.md](PANEL.md). Nach dem Update Home Assistant neu starten. Die Ressource der Dashboard-Karte auf `/stromtarif-card.js?v=0.4.0` ändern; das Panel wird automatisch registriert.
