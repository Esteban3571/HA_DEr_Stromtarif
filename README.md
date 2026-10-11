# Stromtarif für Home Assistant

Version 0.1.0 – lokale HACS Custom Integration, keine separate App / kein Docker-Add-on.

Verwaltet feste Stromtarife, manuelle Zählerstände, Tarifwechsel und Ableseerinnerungen. Alle Daten bleiben in Home Assistant. Mehrere Zähler können als separate Integrationseinträge angelegt werden.

## Installation mit HACS

1. HACS öffnen → Menü → **Benutzerdefinierte Repositories**.
2. `https://github.com/Esteban3571/HA_DEr_Stromtarif` als Kategorie **Integration** hinzufügen.
3. **Stromtarif** herunterladen und Home Assistant neu starten.
4. Einstellungen → Geräte & Dienste → Integration hinzufügen → **Stromtarif**.
5. Tarifname, Startdatum, Anfangszählerstand, Arbeitspreis, monatliche Grundgebühr und Erinnerungsintervall eingeben.

Benötigt Home Assistant **2025.12 oder neuer**. Alternativ `custom_components/stromtarif` nach `/config/custom_components/stromtarif` kopieren und neu starten.

## Bedienung

Unter Einstellungen → Geräte & Dienste → Stromtarif → **Konfigurieren**:

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

Manuelle Ablesungen werden bewusst nicht als zeitgenaue Statistik ins Energie-Dashboard eingespeist: ein Quartalsverbrauch würde sonst dem Eingabezeitpunkt zugeordnet. Diese Version bietet Kosten- und Verbrauchssensoren für normale Dashboards. Die automatische Übernahme eines zukünftigen Verbrauchssensors und rückwirkende Tarifkorrekturen sind noch nicht implementiert.

## Entwicklungsstand und Tests

Erste Version: vor produktiver Nutzung mit einem Testeintrag prüfen. Die Berechnungslogik wird automatisiert getestet; ein echter Lauf in einer Home-Assistant-Installation ist noch erforderlich.

```sh
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

Fehler und Erweiterungswünsche: https://github.com/Esteban3571/HA_DEr_Stromtarif/issues

Lizenz: MIT.
