# Änderungen

## 0.7.0

- Historischer Eingabeassistent mit speicherbaren Entwürfen, Nachbardaten und Grenzdatumvorschlägen.
- Tarifanlage und Rechnungslegung getrennt; unabhängige Rechnungszeiträume.
- Unbekannte Kosten statt Nullwerte und ausdrückliche, markierte Grenzstandschätzungen.
- Geprüfte Übernahme mit Wiederherstellung und Schutz vor veralteten Entwürfen.
- Beide Dashboard-Karten automatisch laden, Standardkonfiguration und doppelte Registrierung absichern.
- 72 Python-Tests und drei Chromium-Testprogramme bestanden.

## 0.6.0

- Kompakte Dashboard-Karte zur manuellen Zählerstandserfassung mit Zählernummer, Datum und kWh-Eingabe.
- Tarifbuchauswahl, optionale Überschrift und vorgewählter Eintrag.
- Korrektur der letzten normalen Ablesung am selben Datum, Revision und erhaltene Eingaben bei Fehlern.
- Chromium-Test und CI-Prüfung der Eingabekarte ergänzt.

## 0.5.0

- Geplante Abschläge per Klick bestätigen und als Zahlung bearbeiten.
- Optionale automatische Verbuchung je Termin mit Schutz vor Doppelbuchung.
- Abschlagänderungen mit Gültigkeitsdatum, Historie und Übernahme in Folgeperioden.
- Wiederkehrende Periodenabrechnungen zum Stichtag ohne Tarifabschluss.
- Zählernummern je Ablesung und physischer Zählerwechsel ohne Verbrauchssprung.
- Migration, Zählerquellen-Neukalibrierung und Zählernummern in Tabellen, CSV und Sensorattributen.
- Dokumentation chronologisch absteigend; Release-Job verwendet nur die aktuelle Version.
- 63 Python-Tests und Chromium-Panel-/Kartentests.

## 0.4.0

- Optionalen, dauerhaft konfigurierbaren Seitenleisten-Eintrag mit vollständigem Verwaltungs-Panel ergänzt.
- Jede Ablesung einzeln bearbeiten; Anfangsstand und Tarifgrenzen synchronisiert korrigieren, normale Ablesungen entfernen.
- Tarife, historische Preise, Abschläge, Zahlungen, Rechnungen und alle bestehenden Geräteoptionen direkt verwalten.
- Effektiven Strompreis inklusive Grundgebühr je Tarif sowie als Sensor und in der Karte anzeigen.
- Verbrauch nach Monat, Quartal und Jahr mit Tarifauswahl, Schätzungskennzeichnung und Teilperioden darstellen.
- Administratorprüfung, atomare Validierung und Datenrevision gegen veraltete Schreibzugriffe.
- Modell-, HA-Laufzeit- und Chromium-Paneltests ergänzt.

## 0.3.0

- Kalender und To-do-Ziele bei Einrichtung, Tarifwechsel und nachträglich wählen.
- Ganztägige Ablese- und Abschlagstermine sowie Ableseaufgaben ohne Neustart-Duplikate.
- Unabhängiger Zahlungsplan: Tag 1–31, Monatsende, individuelle Beträge und dauerhafte Ausnahmen.
- Tarifstatus inaktiv, Endzählerstand und separate Lieferanten-Endabrechnung; neuer Tarif bleibt aktiv.
- Vertragsfreie Zeit nicht dem abgeschlossenen Tarif zurechnen.
- Status, Endabrechnungen und Terminplan in Karte und CSV; Störungsanzeige für Erinnerungsziele.
- Datenmigration ohne Verlust vorhandener Tarif-, Ablese- und Zahlungshistorie.
- Benannte GitHub-Releases nach erfolgreichen CI-Prüfungen mit lesbaren deutschen Versionshinweisen.
- Regressionstests für Monatsende, Schaltjahr, unabhängige Termine, Abschluss, Zielwechsel und echte HA-Kalender/-Aufgaben.

## 0.2.0

- Einrichtungsfehler durch ungültige Schrittweite des Zahlen-Selektors behoben.
- Abrechnungsperiode, monatlichen Abschlagsplan und tatsächlich bezahlte Abschläge getrennt erfassen.
- Kosten-/Saldo-Prognose mit Kennzeichnung von Schätzungen und Abgrenzung geplanter Zahlungen.
- Dashboard-Karte mit Tarif-, Ablese-, Verbrauchs-, Kosten- und Zahlungshistorie; CSV-Download.
- Authentifizierte, auf Administratoren beschränkte Historien- und Exportbefehle.
- Kumulativen Wh-/kWh-Sensor kalibrieren und automatisch übernehmen; manuelle Erfassung bleibt möglich.
- Ausfälle und Resets erkennen; nach erkanntem Reset bis zur Neukalibrierung pausieren.
- Bestehende Tarifbücher beim Laden ohne Verlust der Historie erweitern.
- Home-Assistant-Laufzeit- und Chromium-Kartentests für den Testworkflow ergänzt.

## 0.1.1

- Anzeigename auf DEr Stromtarif geändert.
- HACS- und Home-Assistant-Einrichtungsbuttons in der Anleitung ergänzt.

## 0.1.0

- Feste Stromtarife, manuelle Ablesungen, kalendergenaue Grundgebühr und Ableseerinnerung.
