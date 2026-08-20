# v0.1.3 – THEME-MANAGER UND GEMEINSAMES ERSCHEINUNGSBILD

Themes nach dem Vorbild des BudgetManagers – und eine zentrale Wahl, die für
alle LifePlanner-Module gilt.

## Themes

- `ui/theme_manager.py` mit demselben Aufbau wie im BudgetManager: **zwei**
  Rückfallprofile im Code, alles Weitere als JSON in `ui/profiles`, eigene
  Fassungen im Datenordner.
- Mitgeliefert: Standard Hell/Dunkel, Nord, Solarized Hell/Dunkel, Dracula,
  Warm Sepia, Kontrast Schwarzweiss, OLED Schwarz.
- Ein fehlerhaftes Profil wird übersprungen, protokolliert und in den
  Einstellungen gemeldet – statt die Anwendung farblos starten zu lassen.
- Schriftgröße gehört zum Profil und wird als eigene Fassung gesichert.

Das Stylesheet enthielt vorher rund fünfzig feste Farbwerte. Alle kommen jetzt
aus dem Profil; außerhalb der Profildateien steht in der gesamten Oberfläche
kein einziger Farbwert mehr.

## Zentral für alle Module

Neu in den Einstellungen: **„Für alle LifePlanner-Module übernehmen"**. Der
Haken schreibt das Theme nach
`$LIFEPLANNER_BRIDGE_DIR/shared_theme.json` (Schema `lifeplanner.theme.v1`),
wo BudgetManager, FPM und der LifePlanner es lesen können. Umgekehrt folgt der
FreizeitManager der zentralen Wahl, solange **„Gemeinsames Theme des
LifePlanners übernehmen"** eingeschaltet ist.

Drei Regeln, bewusst so gewählt (siehe `docs/GEMEINSAMES_THEME.md`):

1. Lesen ist freiwillig – ohne den Haken gilt die lokale Wahl.
2. Schreiben ist eine ausdrückliche Handlung – ein Modul, das beim Start
   ungefragt sein Theme veröffentlicht, würde die Wahl aller anderen
   überschreiben.
3. Ohne Host passiert nichts; die Bedienelemente sind dann ausgegraut.

Der Austausch läuft über den Bridge-Ordner, weil der Modul-Host-Vertrag den
Zugriff auf fremde Datenbanken verbietet. Eine beschädigte Datei wird
ignoriert, nicht übernommen.

## Behobene Fehler

Vier Lesbarkeitsfehler, die erst am gerenderten Fenster auffielen:

- **Die Seitenleiste war in dunklen Themes unlesbar.** Ihr Text nutzte
  `text_invers` – gedacht als Text auf der Akzentfarbe. Sie hat jetzt einen
  eigenen Farbschlüssel.
- **Die Kacheln blieben weiß.** Ihr Inline-Stylesheet überschreibt das
  Anwendungs-Stylesheet und enthielt feste Farben.
- **Ein Themewechsel kam bei Kacheln und Karten nicht an**, weil `refresh()`
  nur den Inhalt erneuert, nicht den Inline-Stil. Die Seiten werden jetzt neu
  aufgebaut – wie beim Sprachwechsel.
- **Der Modusknopf war ein leeres Rechteck.** Er steht in der Seitenleiste,
  trug aber die Panel-Farben.

Dazu zwei Dinge, die vorher schon schief waren:

- Der Einstellungsseite fehlte ein **Scrollbereich**; bei 800 px Fensterhöhe
  quetschte Qt die Gruppen bis zur Überlappung ineinander.
- Kontrollkästchen hatten kein sichtbares Kästchen.

## Tests

87 statt 85. `tests/test_theme.py` prüft unter anderem, dass jedes Profil alle
Farbschlüssel abdeckt, dass eine kaputte Profildatei übersprungen statt
verschluckt wird, dass ein zweites Modul das gemeinsame Theme übernimmt und
dass eine beschädigte Bridge-Datei keinen Schaden anrichtet.

Neu ist ein **Kontrasttest** über vierzehn Farbpaare in jedem Profil. Er hat
sofort zwei zu blasse Sekundärtexte in den Solarized-Profilen gefunden; beide
sind korrigiert.

# v0.1.2 – DEUTSCH, ENGLISCH, FRANZÖSISCH

Die Oberfläche spricht jetzt drei Sprachen. Die Umschaltung greift sofort,
ohne Neustart.

## Übersetzungssystem

- `freizeitmanager/i18n/` mit `de.json`, `en.json`, `fr.json` – je 216
  Schlüssel, Aufbau wie bei FPM (Punktschreibweise, Deutsch als Rückfallebene).
- Ein unbekannter Schlüssel liefert den Schlüssel selbst zurück, statt die
  Oberfläche mit einer Ausnahme abzubrechen. Dasselbe gilt für einen fehlenden
  Platzhalter.
- Die Sprache steht ganz oben in den Einstellungen: Wer sie sucht, versteht
  den Rest der Seite womöglich noch nicht.

## Datum und Wochentage gehören zur Sprache

`strftime` gibt Wochentagsnamen in der Sprache des Betriebssystems aus, nicht
in der gewählten. Deshalb kommen Wochentage aus den Sprachdateien und das
Datumsformat aus der Sprache: `20.08.2026` im Deutschen, `20/08/2026` im
Englischen und Französischen.

## Begründungen sind Schlüssel, kein Text

Die Rotation Engine speichert ihre Begründungen als `(Schlüssel, Parameter)`
und übersetzt erst beim Anzeigen. Eine bereits berechnete Bewertung bleibt
nach einem Sprachwechsel gültig, ohne neu gerechnet zu werden. Aus demselben
Grund sind Dringlichkeits- und Vorschlagsbeschriftungen Funktionen statt
Modulkonstanten: Ein Dict wird beim Import ausgewertet und würde die Sprache
einfrieren, die beim Programmstart aktiv war.

Beziehungsgrade und Gruppen werden dagegen einmalig beim ersten Start in der
aktiven Sprache angelegt und danach nie wieder angefasst – es sind Nutzerdaten,
die man umbenennen können muss.

## Behobene Fehler

- **Die Sprachdateien fehlten im PyInstaller-Paket.** Die gebaute Anwendung
  hätte überall nur noch Schlüssel angezeigt. Sie werden jetzt mitgeliefert,
  und `translator.py` findet sie auch unter `sys._MEIPASS`.
- **`t` war in `dialogs.py` nicht importiert.** Ein Klick auf „Neuer Kontakt“
  hätte die Anwendung mit einem `NameError` begrüßt. Kein Test hat je einen
  Dialog geöffnet – diese Lücke ist mit `tests/test_dialogs.py` geschlossen.
- Der erste Versuch, fehlende Sprachdateien im Selbsttest zu erkennen, schlug
  nie an: `set_language` fällt bei einer fehlenden Datei still auf Deutsch
  zurück. Geprüft wird jetzt die Datei selbst, nicht das Ergebnis von `t()`.

## Tests

68 statt 49. Neu:

- `test_dialogs.py` – jeder Dialog wird in jeder Sprache wirklich aufgebaut.
- `test_i18n_completeness.py` – gleiche Schlüsselmenge, gleiche Platzhalter,
  gleiche Listenlängen in allen Sprachen; dazu ein Lauf durch alle Seiten in
  allen Sprachen, der nach unaufgelösten Schlüsseln sucht. Gegengeprüft: Mit
  einem absichtlich vergessenen `t()` schlägt er fehl.
- `main.py --smoke` prüft zusätzlich, dass alle Sprachdateien im Paket liegen.
  Gegengeprüft am gebauten Programm: Ohne `fr.json` bricht er mit Exitcode 1 ab.

# v0.1.1 – RELEASE-PIPELINE UND INSTALLIERBARE MODULE

0.1.0 lieferte nur Quellcode aus. Ab dieser Version entsteht bei jedem Tag ein
installierbares LifePlanner-Modul für Linux und Windows.

## Pipeline

- `.github/workflows/ci.yml` prüft bei jedem Push Version, Linting, Tests und
  einen GUI-Rauchtest.
- `.github/workflows/release.yml` läuft auf einen Tag `v*` in drei Stufen:
  **prüfen** (Tag, `version.json`, `app_info` und `module.json` müssen
  übereinstimmen; Linting, Tests, Rauchtest), **bauen** (PyInstaller auf Linux
  und Windows), **veröffentlichen** (Module packen, gegen den Host-Vertrag
  prüfen, Prüfsummen, Release).
- Gebaut wird nur, was vorher geprüft wurde. Veröffentlicht wird nur, was
  `tools/verify_lpmodule.py` akzeptiert.

## Werkzeuge

- `tools/sync_version.py` – die Version steht nur in `version.json`; alles
  andere wird abgeleitet. `--check --expect-tag` bricht ab, bevor ein Paket mit
  falscher Version entsteht.
- `tools/build_lifeplanner_module.py` – packt eine gebaute Runtime als
  `.lpmodule` (`component.json` im Schema `lifeplanner.component.v1`,
  `payload/`, `payload_sha256`). Das Ausführbit wird direkt ins Archiv
  geschrieben, weil CI-Artefakte Unix-Rechte verlieren und das Linux-Paket auf
  einem Windows-Runner entstehen kann. Ohne das startet das installierte Modul
  mit „[Errno 13] Keine Berechtigung“.
- `tools/verify_lpmodule.py` – prüft das fertige Archiv so, wie der LifePlanner
  es prüfen würde: Schema, Version, Plattform, Programm vorhanden und
  ausführbar, `payload_sha256` über den tatsächlichen Inhalt.
- `tools/gui_smoke_test.py` und `main.py --smoke` – das gebaute Programm baut
  Datenbank und Fenster auf und beendet sich. Das fängt fehlende
  PyInstaller-Importe ab: das häufigste Muster, bei dem ein Paket entsteht,
  beim Doppelklick aber nichts passiert.

## Signatur

Ed25519 ist vorbereitet, aber optional. Ohne hinterlegten Schlüssel entstehen
sichtbar unsignierte Pakete, die der Host erst nach manueller Bestätigung
annimmt. Ist ein Schlüssel gesetzt, wird `component.json` signiert und die
Pipeline prüft die Signatur vor dem Hochladen.

## Verworfene Optimierung

Ein Filter, der ungenutzte Qt-Bibliotheken (Quick, QML, PDF) aus dem Paket
strich, sparte 15 Prozent Größe – hinterließ aber Symlinks, die ins Leere
zeigten. Die Anwendung startete trotzdem, weil sie diese Bibliotheken nie lädt;
der Defekt fiel erst beim Packen auf. Der Filter ist entfernt. Stattdessen
bricht der Paketierer jetzt ab, wenn eine Runtime baumelnde Symlinks enthält.

## Sonstiges

- `ruff.toml` pinnt die Regelauswahl, damit lokale Läufe und CI dasselbe sagen.
- 49 Tests, davon 15 zur Paketierung.

# v0.1.0 – FREIZEITMANAGER: KONTAKTROTATION MIT BEZIEHUNGSFRISCHE

Erster Stand des FreizeitManagers. Der bisherige Kontaktmanager liegt unter
`legacy/` und wird von keinem neuen Code mehr benutzt.

## Warum ein Neubau

- `termine.db` wurde im **Arbeitsverzeichnis** angelegt. Je nach Startort landete
  die Datenbank in `Downloads/`, `Desktop/` oder einem beliebigen anderen Ordner.
- Gruppen und Beziehungsgrade wurden als Freitext nach `kontakte` kopiert.
  Umbenennen oder Löschen erzeugte verwaiste Werte.
- Die Registerkarte „TAGs“ verwaltete in Wahrheit Beziehungsgrade.
- Die Kapazitätseinstellungen (Tage pro Woche, Wochenenden pro Monat, erlaubte
  Wochentage) wurden gespeichert, aber nie ausgewertet.
- Die gesamte Programmlogik lag in einer 582-Zeilen-`main.py`.

Der alte Bestand enthielt keine Kontakte, sondern nur Gruppen, Beziehungsgrade
und Einstellungen. Diese werden beim ersten Start einmalig übernommen und dabei
in echte Datensätze aufgelöst.

## Engine

Läuft vollständig ohne Qt und ist damit einzeln prüfbar.

- **Beziehungsfrische** ersetzt `letztes_treffen`. Jede Interaktionsart hat eine
  eigene Grundwirkung, die exponentiell abklingt; die Halbwertszeit ist der
  gewünschte Kontaktrhythmus der Person. Damit nimmt eine Reaktion oder eine
  kurze Nachricht einen überfälligen Freund nicht mehr aus der Rotation.
  Werte über 1,0 sind Guthaben: Nach einem intensiven gemeinsamen Tag ist der
  nächste Kontakt später fällig.
- **Harte Regeln und Kapazität**: Status, Pause, Zurückstellung, bereits
  geplanter Termin, Sperrfrist. Wochen- und Wochenendbudget schwächen Vorschläge
  ab (Telefonat statt Treffen), statt sie zu verbieten. Nur substanzielle
  Kontakte lösen eine Sperrfrist aus.
- **Rotation** aus Fälligkeit, Wichtigkeit, Funkstille, Kontext, Fairness und
  manuellem Wunsch. Wichtigkeit moduliert die Fälligkeit (Faktor 0,7–1,1), statt
  nur Punkte zu addieren – sonst verdrängt eine lose Bekanntschaft mit einem
  halben Jahr Funkstille einen engen Freund mit einem Monat.
- **Fokus**: aus allen Kandidaten werden höchstens drei sichtbar. Wer die
  Anwendung drei Wochen nicht öffnet, sieht danach keinen Schuldenberg.

## Datenmodell

- Gruppen, Tags und Beziehungsgrad sind drei getrennte Konzepte mit echten
  Fremdschlüsseln. Eine Gruppe umbenennen bricht keine Referenz mehr.
- Vollständige Interaktionshistorie statt eines einzelnen Datums.
- Wichtigkeit und gewünschter Rhythmus sind getrennte Felder.
- Schemaversionierung, Sicherungen, Pfadauflösung mit Vorrang für den Host.

## Oberfläche

- Cockpit mit vier responsiven Kacheln (4 / 2 / 1 Spalten) und höchstens drei
  Vorschlagskarten. Jede Karte hat genau eine Hauptaktion, die mit einem Klick
  ohne Rückfrage schreibt – die Kontaktart steht durch den Vorschlag fest.
- Energiezustand (wenig Energie / normal / Lust auf Leute) ändert die
  Vorschläge sofort. „Andere Vorschläge“ zeigt andere Personen.
- Ist nichts fällig, verschwindet die Liste und es erscheint eine einzelne
  Entwarnungskarte. Leere Bereiche werden ausgeblendet statt leer angezeigt.
- Einfachmodus als Start, Expertenmodus (Strg+E) blendet die Rotationsansicht
  ein – die einzige Stelle, an der eine Punktzahl sichtbar wird.
- Dringlichkeit läuft über einen farbigen Punkt und den farbigen Kartenrand,
  nicht über Emoji: Zeichen wie U+1F7E0 fehlen in vielen Systemschriften und
  erscheinen dort als leere Lücke.

## LifePlanner

Nach `docs/MODUL_HOST_VERTRAG.md` v1:

- `module.json` im Schema `lifeplanner.module.v1`, eigener Prozess, eigener
  Datenordner über `FREIZEITMANAGER_DATA_DIR` bzw. `LIFEPLANNER_MODULE_DATA_DIR`.
- Austausch über eine atomar geschriebene JSONL-Outbox im Bridge-Ordner. Es
  werden nur Zählwerte und die nächsten Schritte veröffentlicht, niemals Notizen
  oder Rohdaten. Kein Zugriff auf fremde Datenbanken.
- Ohne gesetzte Host-Variablen sind Bridge und Events stille No-Ops; die
  Anwendung läuft vollständig eigenständig.

## Tests

34 Tests, davon 8 UI-Rauchtests, die die Schnellaktionen tatsächlich auslösen
und prüfen, dass sie in der Datenbank landen.

    QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q

## Noch nicht enthalten

Hobbys und Aktivitäten (0.2) sowie Kalenderzugriff (0.3) sind im Datenmodell
und in der Architektur vorgesehen, aber nicht gebaut.
