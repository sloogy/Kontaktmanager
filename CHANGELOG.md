# Changelog

## 0.2.1 — 23. August 2026

Zwei Funde aus einem Probelauf der Typprüfung, und der Weg dorthin ist
dokumentiert.

### Ordnung

- **Zwei Funde aus einem Probelauf der Typprüfung.**
  `QGuiApplication.instance().styleHints()` in `theme_manager.py` — der Umweg
  über `instance()` war länger und zwang zu einer `None`-Prüfung, die nichts
  sicherer macht; `styleHints()` ist statisch. Dieselbe Stelle gab es im
  LifePlanner. Und in `rule_engine.py` liefen vier Schleifen über zwei
  verschiedene Tabellen, alle mit der Variablen `row`: kein Fehler, aber wer
  die Stelle las, musste zurückblättern.

  Die Prüfung selbst ist noch nicht eingeschaltet. `docs/TYPPRUEFUNG.md` hält
  fest, warum: Von 84 Meldungen haben 67 dieselbe Wurzel — das Datenmodell
  deklariert 62 Spalten in der alten SQLAlchemy-Schreibweise, und ohne Typ
  weiß mypy an keiner Verwendungsstelle etwas. Der Umbau gehört in einen
  Schritt, in dem das Programm auch bedient werden kann.

## 0.2.0 — 23. August 2026

Die Vorschläge des Fokus-Cockpits erscheinen jetzt auch im
LifePlanner-Dashboard — bewusst nie als dringend, denn ein Schuldenberg soll
auch dort keiner entstehen. Dazu ein stummer Schlucker, den der
Ausnahmen-Ratchet bis Loop 45 nicht sehen konnte.

### Funktion

- **Die Vorschläge des Cockpits erscheinen jetzt auch im LifePlanner.** Das
  Schema `lifeplanner.notice.v1` stammt aus genau diesem Modul: `publish_focus`
  schrieb solche Meldungen als einziges — nur in einem eigenen Format, das nur
  der Host kannte. Seit LifePlanner 0.5.16 lesen alle Module dasselbe, und der
  FreizeitManager hängt jetzt daran.

  Beides bleibt bestehen: `freizeitmanager.focus.v1` trägt weiterhin die
  Zählwerte der Fokus-Zusammenfassung, die neue Datei die Meldungen.

  **Keine Stufe wird `kritisch`.** Eine Freundschaft, die still geworden ist,
  ist kein Alarm — sie würde im Host sonst neben einem überzogenen Budget
  stehen. Das Programm ist ausdrücklich so gebaut, dass es keinen Schuldenberg
  aufbaut; das gilt auch für das Dashboard des Hosts. Höchstens drei Meldungen,
  wie im Cockpit. Ein Test hält beides fest. Handbuch in drei Sprachen.

### Dokumentation

- **Das README sagt jetzt zuerst, was das Programm tut.** Vorher stand dort
  Technik: eine Tabelle aus Dateipfaden. Die fachlich stärksten Passagen —
  Beziehungsfrische, „kein Schuldenberg" — lagen zwischen Build-Kommandos
  begraben und sind jetzt oben. Wer wissen wollte, wofür das Programm da ist,
  fand einen Satz und danach die Bauanleitung. Der fachliche Teil steht jetzt
  vorn und beantwortet, was man mit dem Programm tut und für wen es gedacht
  ist; das Technische folgt darunter. Drei Tests halten die Reihenfolge fest.

### Sicherheit

- **Ein stummer Schlucker, den der Ratchet nicht sehen konnte.** Der
  Ausnahmen-Ratchet zählt `except Exception: pass` und deckelt die Zahl —
  kannte aber nur `except`-Handler. In `i18n/translator.py` stand dieselbe
  Sache als `contextlib.suppress(KeyError, IndexError, ValueError)`: Ein
  fehlender Platzhalter in einem Übersetzungstext blieb spurlos, der Nutzer
  sah `{name}` im Text und niemand erfuhr, in welchem Schlüssel es klemmt.
  Der FreizeitManager galt darum als das Programm mit null stummen
  Stellen — er hatte eine. Sie meldet jetzt über
  `defensive_log.uebersprungen()`, ohne den Ablauf zu ändern; der Ratchet
  zählt `suppress` in allen vier Programmen mit.

### Ordnung

- **Der `legacy/`-Ordner fiel aus jeder Prüfung.** Die drei Workflows riefen
  `ruff check freizeitmanager tools tests main.py` auf — eine Ordnerliste, die
  bei jedem neuen Verzeichnis stillschweigend eine Lücke bekommt. Der
  Ausschluss steht jetzt als `exclude` in `ruff.toml`, und geprüft wird
  `ruff check .` wie in den anderen drei Programmen.

## 0.1.13 — 22. August 2026

### Stabilität

- **Das Lint-Gate machte sich selbst rot.** `ruff` stand als Bereich in den
  Bauabhängigkeiten. Eine neue Nebenversion brachte neue Regeln mit, und weil
  der Lint-Lauf im `check`-Job vor `build` und `publish` steht, fiel mit dem
  Gate auch das Release aus — ohne dass sich eine Zeile Code geändert hätte.
  **Jeder Lauf war so rot, zurück bis 0.1.10:** Die Tags v0.1.10 bis v0.1.12
  stehen, veröffentlicht wurde nie etwas. `ruff` steht jetzt exakt auf
  0.16.3, derselben Version wie in den anderen drei Programmen und wie lokal
  installiert. Ein Test hält das fest: Bereich ist ein Fehler, und die lokal
  installierte Version muss zur Pinnung passen.

### Sicherheit

- **Der Verifizierer kannte den eigenen Modulvertrag nicht.** `module.json`
  deklariert seit dem v2-Umbau `lifeplanner.module.v2`, der Paketbauer
  akzeptiert beide Schemata — nur `tools/verify_lpmodule.py`, das letzte Tor
  vor der Veröffentlichung, prüfte weiter hart auf v1. Er hätte jedes eigene
  Paket abgelehnt. Dieselbe Regel stand ein drittes Mal in `app_info.py`,
  dort ebenfalls als v1; die Konstante las niemand — genau darum fiel es nicht
  auf. Der Verifizierer verlangt bei v2 zusätzlich, dass `requires_host` in
  `module.json` und `component.json` übereinstimmt: Der Host liest die
  Anforderung aus dem Manifest, der Installer aus den Paketdaten.

### Bedienung

- **Menüleiste.** Datei / Ansicht / Extras / Hilfe an derselben Stelle wie in
  den drei anderen Programmen der Suite. Expertenseiten bleiben im
  Einfachmodus auch im Menü ausgeblendet.
- **Der Datenordner lässt sich öffnen**, und Name, Version und Datenordner
  stehen erstmals irgendwo im Programm.

## 0.1.12 — 22. August 2026

- Release-Trigger fail-closed und reproduzierbar; Wiederholungen tragen einen
  überprüfbaren Erfolgsmarker und verschieben den Release-Tag nicht.

## 0.1.11 — 22. August 2026

- Pakettests auf den v2-Hostvertrag umgestellt; der Paketbauer unterstützt
  `lifeplanner.module.v2`.

## 0.1.10 — 22. August 2026

### LifePlanner-Integration

- **Fachevents folgen dem LifePlanner-Eventvertrag.** Ein kompatibler
  Eventwriter ergänzt den bisherigen, und Regressionstests halten das Format
  fest.
- **`lifeplanner.module.v2` wird deklariert.**

## 0.1.9 – 22. August 2026

### Stabilität

- **Bei jedem Push nach main laufen jetzt die Gates.** Vorher lief dort gar
  nichts: Der volle Lauf hängt am Tag beziehungsweise an einem
  `[release]`-Commit, gearbeitet wird in dieser Suite aber direkt auf main.
  Ein Fehler wäre erst beim nächsten Release aufgefallen — bis zu zehn
  Arbeitsrunden später. Der neue Lauf ist bewusst schlank: Linux, ein Python,
  keine Builds, zwei bis drei Minuten. Er reagiert nur auf main, nie auf Tags,
  damit das Doppellauf-Problem nicht zurückkommt, das den Push-Trigger im
  Release-Workflow ausgeschlossen hatte.
- **Der Ausnahmen-Ratchet ist eingebaut**, in CI und Release-Lauf. Er prüft
  über den Syntaxbaum und erfasst alles außerhalb von Tests und Werkzeugen:
  keine nackten `except:`, kein `except BaseException`, gedeckelte stumme
  Schlucker (`except Exception: pass`), gedeckelte breite Handler. Der
  FreizeitManager steht mit vier breiten und null stummen Handlern am besten
  von den vier Programmen da — der Ratchet hält das fest.

## 0.1.8 – 22. August 2026

### Sicherheit

- **Die Datenbank liegt nicht mehr offen.** Sie trägt Namen, Geburtstage,
  Telefonnummern und private Notizen zu anderen Menschen — Daten Dritter, die
  diese dem Programm nie selbst anvertraut haben. Angelegt wurde sie bisher
  mit dem Standard-umask, auf typischen Linux-Systemen also weltlesbar. Jetzt
  0600, ebenso jede Sicherung.
- **Modulpakete werden beim Entpacken geprüft.** Vorher stand dort ein blankes
  `extractall` — und zwar genau an der Stelle, wo ein gerade hereingekommenes
  Paket geprüft wird, dessen Signatur noch gar nicht kontrolliert ist.

### Stabilität

- **Die Sicherung ist in sich stimmig.** Sie war ein `copy2` der
  Datenbankdatei; eine SQLite-Datei lässt sich so nicht gefahrlos kopieren,
  während jemand hineinschreibt. Jetzt über die Online-Backup-Schnittstelle,
  mit Integritätsprüfung — und die zwanzig jüngsten werden aufgehoben.
- **Nur eine Instanz je Datenordner.** Zwei Instanzen lasen den Stand beim
  Start und schrieben unabhängig weiter.
- **Die Logdatei wächst nicht mehr unbegrenzt.**

### Darstellung

- Ränder und Abstände folgen jetzt auch der eingestellten Schrift, nicht nur
  die Schriftgrösse selbst.

## 0.1.7 – 21. August 2026

### Die Oberfläche wächst mit der Schriftgröße

Ränder, Abstände und Rundungen folgten nur der Bedien-Skalierung, nicht der
eingestellten Schrift. Wer die Schrift zur besseren Lesbarkeit hochstellte,
bekam grösseren Text in unverändert engen Feldern.

- Zwei Faktoren, bewusst getrennt: Die Bedien-Skalierung und die Profilschrift
  wirken gemeinsam auf Masse, aber nicht doppelt auf die Schriftgrösse selbst.
- Abgestufte Radien nach dem Vorbild des BudgetManagers: Eingaben 4,
  Schaltflächen 6, Karten und Gruppen 8. Karten standen vorher bei 9 — eine
  eigene Stufe, die sich mit keinem der anderen Programme deckte.

## 0.1.6 – 21. August 2026

### Die Modulpakete werden signiert ausgeliefert

Die Signierung war vollständig vorbereitet, es fehlten nur die Schlüssel. Ohne
sie fiel der Release-Lauf still auf `--allow-unsigned` zurück: Die
`.lpmodule`-Pakete gingen unsigniert heraus, und der LifePlanner verlangte bei
der Installation eine ausdrückliche Vertrauensbestätigung.

- Die Schlüssel liegen jetzt im Repository hinterlegt.
- Beide Stellen sind fail-closed statt stillschweigend nachgiebig: Fehlt der
  Schlüssel, bricht der Lauf ab, statt unsigniert weiterzubauen. Fehlte
  vorher der öffentliche Schlüssel, lief die Prüfung ohne ihn ins Leere und
  meldete trotzdem Erfolg.

### Das Handbuch gibt es jetzt auf Deutsch, Englisch und Französisch

Erzeugt wurde bisher nur die deutsche Fassung, obwohl die Hilfetexte selbst
längst übersetzt vorlagen. Wer das Programm auf Englisch oder Französisch
benutzte, fand daneben ein deutsches Handbuch.

- `docs/USER_GUIDE.{de,en,fr}.md` und die zugehörigen Hilfeseiten entstehen
  aus derselben Quelle wie die Hilfe in der Anwendung.
- Die Seiten tragen die passende Sprachauszeichnung, damit Vorleseprogramme
  französischen Text nicht deutsch aussprechen.
- Anker vertragen Akzente: Aus „Fraîcheur" wurde vorher „fra-cheur".

### Das Design folgt auf Wunsch dem Betriebssystem

- Neue Einstellung: Stellt das Betriebssystem auf dunkel um, wechselt das
  Programm mit. Weil es zu einem dunklen Profil kein automatisches helles
  Gegenstück gibt, wählen Sie beide Seiten selbst.
- Standard ist aus — eine getroffene Wahl bleibt bestehen. Meldet die
  Plattform nichts, wird nicht auf gut Glück hell angenommen. Im LifePlanner
  behält dessen zentrale Darstellung den Vorrang.

# v0.1.5 – RELEASEGATE: RUFF WIEDER GRÜN

- Der Releaselauf zu 0.1.4 scheiterte an `ruff`. Behoben: `Iterable` und
  `Sequence` kommen aus `collections.abc`, `RowAction` ist eine `StrEnum` statt
  einer `(str, Enum)`-Mischung, eine Yoda-Bedingung im Test steht wieder herum,
  und zwei Importblöcke sind sortiert.
- Vier der fünf Funde stammten aus dem Import-Zweig und kamen mit dessen Merge
  nach `main` mit; einer war neu aus `tools/design_sync.py`.

# v0.1.4 – GEMEINSAMER DESIGNKATALOG

### Ein gemeinsamer Designkatalog

LifePlanner, BudgetManager, FountainPen Manager und FreizeitManager liefern
jetzt dieselben **26 Designs** aus — byteweise dieselben Profildateien, erzeugt
und geprüft von `tools/design_sync.py`.

**Warum das nötig war.** Vorher kannten BudgetManager und LifePlanner 26 Designs
mit 29 Rollen, FPM und FreizeitManager sieben mit 38–40. Wer im LifePlanner ein
Design wählte, das ein Modul nicht selbst mitbrachte, bekam dort dessen
Hintergrund, aber Standardblau für Akzent, Karten und Statusfarben — was der
Host nicht mitliefert, fällt im Modul auf das eingebaute Profil zurück. Und drei
Designs trugen in beiden Lagern verschiedene Namen (`Kontrast - Schwarz/Weiß`
gegen `Kontrast Schwarzweiss`, `Hell - Warm (Sepia)` gegen `Warm Sepia - Hell`,
`Dunkel - OLED (Kontrastarm)` gegen `OLED Schwarz`), sodass das Modul das
Hostprofil unter einem Namen suchte, den es selbst nicht führte.

- **55 Rollen je Profil** — ein Kern von 33 für alle Programme plus die
  Bedeutungsfarben der einzelnen. Fehlende Rollen wurden nicht erfunden, sondern
  aus vorhandenen Farben desselben Profils abgeleitet; handverlesene Werte
  blieben unangetastet. Wo zwei Programme dieselbe Rolle unterschiedlich
  führten, gilt der Wert des Hosts.
- **Der Name des Hosts gilt.** Gespeicherte Einstellungen lösen über Aliase
  weiterhin auf.
- **Die Schriftgröße bedeutet überall dasselbe:** 10 heißt normal. Der
  FreizeitManager zeichnet dabei weiterhin 14 Punkt und rechnet den gemeinsamen
  Wert als Faktor darauf um.

### Lesbarkeit ist jetzt Bedingung, nicht Zufall

- **4,5:1 für jede Schrift auf jedem Grund** — die strengste der vier bisherigen
  Schwellen, übernommen aus dem BudgetManager.
- **Die Seitenleiste folgt der Helligkeit des Profils.** Schrift, die auf ihr
  nicht lesbar ist, wird verworfen und neu abgeleitet — in „Solarized – Hell“
  war sie exakt die Farbe der Leiste selbst.
- **Signalfarben heben sich mit mindestens 2,6:1 von der Karte ab.** Ein
  abgeleitetes Gelb erreichte 1,77:1 und war als Ampelfarbe wertlos.
- **Gedimmte Schrift unterscheidet sich messbar von der normalen.** In
  „Solarized – Dunkel“ waren `text` und `text_gedimmt` buchstäblich derselbe Wert.
- **Farbfehlsichtigkeit wird geprüft.** Erfolg/Warnung/Gefahr, die Budget-Typen,
  die vier FPM-Bereiche und die fünf Dringlichkeitsstufen müssen auch bei
  Protanopie, Deuteranopie und Tritanopie unterscheidbar bleiben (Simulation nach
  Viénot/Brettel/Mollon 1999). Vorher waren **348 von 1716 Farbpaaren** nicht
  auseinanderzuhalten, teils sogar identisch — jetzt keines. Repariert wird über
  Helligkeit und Sättigung, nie über den Farbton; der geht dabei gerade verloren.

### Werkzeug

- `tools/design_sync.py check` prüft die eigenen Profile, `build` erzeugt den
  Katalog in allen vier Programmen, `preview` schreibt eine HTML-Übersicht (mit
  den Signalfarben, wie Farbfehlsichtige sie sehen), und `new --name … --akzent …`
  baut aus einer Akzentfarbe ein vollständiges, regelkonformes Design.
- **`build` ist ein Fixpunkt.** Jede Profildatei führt mit, welche Rollen erzeugt
  (`_abgeleitet`) und welche nur nachjustiert wurden (`_vorlage`) — sonst wanderte
  der Katalog mit jedem Lauf ein Stück weiter, statt reproduzierbar zu sein.
- `tests/test_shared_design.py` hält den Katalog zusammen;
  `docs/GEMEINSAMES_DESIGN.md` erklärt Aufbau und Regeln.


### Weiteres
- Die eingebauten Rückfallprofile heißen jetzt wie der Katalog: `Standard - Hell`
  und `Standard - Dunkel`.
- `ThemeProfile.point_size` rechnet den gemeinsamen Wert in die eigene
  Schriftgröße um. Am Schriftbild ändert sich nichts.

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
