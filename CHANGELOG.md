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
