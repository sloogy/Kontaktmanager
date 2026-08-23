# FreizeitManager

Der FreizeitManager hilft dabei, Freundschaften zu pflegen, ohne dass daraus
eine Pflichtenliste wird.

Er beantwortet nicht die Frage „wann habe ich wen zuletzt gesehen?" — die
beantwortet ein Kalender auch. Er beantwortet:
**„Was wäre jetzt eine gute, realistische Aktion für mich?"**

## Was du damit tust

**Menschen eintragen, die dir wichtig sind.** Zu jedem Kontakt gehört, wie
wichtig er dir ist und in welchem Rhythmus du dich melden möchtest — beides
getrennt, denn ein enger Freund am anderen Ende der Welt ist wichtig und
trotzdem nicht wöchentlich zu sehen.

**Festhalten, was war.** Getroffen, angerufen, geschrieben. Ein Klick, keine
Rückfrage. Jede Art von Kontakt zählt unterschiedlich viel: Ein langes
Telefonat wiegt schwerer als ein Geburtstags-Emoji.

**Sehen, was jetzt dran wäre.** Das Cockpit zeigt höchstens drei Vorschläge —
nie mehr. Zu jedem steht, warum gerade dieser Mensch vorgeschlagen wird. Wenn
gerade nichts ansteht, steht das da, und sonst nichts.

**Nein sagen dürfen.** Jeder Vorschlag lässt sich zurückstellen, ganze Kontakte
pausieren. Wie viel du dir pro Woche zumutest und an welchen Tagen, sagst du dem
Programm — es schlägt dann eher ein Telefonat vor als ein Treffen, statt dich zu
überfordern.

**Termine planen.** Was du vorhast, wird eingetragen und zählt dann nicht mehr
als offene Fälligkeit.

## Warum es nicht wie eine Aufgabenliste funktioniert

Eine Liste mit „letztes Treffen: vor 42 Tagen" erzeugt genau zwei Zustände:
erledigt oder schuldig. Der FreizeitManager rechnet stattdessen mit
**Beziehungsfrische** — jeder Kontakt wirkt und klingt mit der Zeit ab, je nach
gewünschtem Rhythmus der Person.

```
Treffen vor 42 Tagen, Ziel 21 Tage                   → überfällig (Faktor 2,2)
… plus Emoji von gestern                             → immer noch überfällig (1,9)
… plus langes Telefonat vor 3 Tagen                  → nicht mehr fällig (0,15)
```

Ein „Happy Birthday 🎂" darf einen engen Freund nicht für 30 Tage aus der
Rotation nehmen. Frische über 1,0 ist **Guthaben**: Nach einem intensiven
gemeinsamen Wochenende ist der nächste Kontakt später fällig als nach einem
Kaffee.

### Kein Schuldenberg

Wer die App drei Wochen nicht öffnet, sieht danach nicht „🔴 17 überfällige
Freundschaften", sondern drei sinnvolle nächste Schritte und den Satz
*„Schön, dass du wieder da bist."* Die anderen vierzehn bleiben intern
bewertet, aber unsichtbar.

Nach außen gibt das Programm nie eine Punktzahl aus, sondern eine
Dringlichkeitsstufe, eine Empfehlung und lesbare Gründe. Die Punktzahl gibt es
nur im Expertenmodus, für alle, die es genauer wissen wollen.

### Fairness statt Bestenliste

Wer nie im Fokus war, bekommt Vorrang; wer gestern dran war, tritt zurück. Ohne
das gewinnen immer dieselben drei Menschen, und der Rest verschwindet still.

## Für wen

Für Menschen, die viele Freundschaften haben und merken, dass die
unaufdringlichen darunter leiden — nicht aus Desinteresse, sondern weil die
lauten zuerst drankommen.

Alle Daten bleiben auf dem eigenen Rechner: Namen, Geburtstage, private Notizen
zu anderen Menschen. Kein Konto, keine Cloud, keine Telemetrie.

Oberfläche auf Deutsch, Englisch und Französisch.

## Als eigenständiges Programm oder als Modul

Der FreizeitManager läuft für sich allein. Er läuft ebenso als Modul im
[LifePlanner](https://github.com/sloogy/Livemanager), zusammen mit BudgetManager
und FountainPen Manager unter einem Dach.

## Loslegen

```bash
python3 main.py
```

Aus dem Quellcode: Python 3.11 oder neuer. Fertige Pakete stehen unter
[Releases](https://github.com/sloogy/Kontaktmanager/releases).

Noch nicht gebaut: Hobbys und Aktivitäten als eigener Bereich, und der Zugriff
auf einen Kalender.

---

Ab hier geht es darum, wie das Programm gebaut ist — für die Weiterentwicklung,
nicht für die Benutzung.

## Die Engine in sechs Schichten


1. **Harte Regeln** (`rule_engine.check_contact`) filtern, wer gar nicht
   vorgeschlagen werden darf: pausiert, zurückgestellt, Termin schon geplant,
   gerade erst richtiger Kontakt gewesen.
2. **Beziehungsfrische** (`freshness.compute_freshness`) ersetzt
   `letztes_treffen`. Jede Interaktion hat eine Wirkung, die exponentiell
   abklingt. Halbwertszeit = gewünschter Rhythmus der Person.
3. **Wichtigkeit und Rhythmus** sind getrennte Felder. Wichtigkeit moduliert
   die Fälligkeit (Faktor 0,7–1,1), statt nur Punkte zu addieren.
4. **Kontext und Kapazität**: Energiezustand, Wochenbudget, Wochenendbudget,
   erlaubte Wochentage. Sie schwächen Vorschläge ab (Telefonat statt Treffen),
   statt sie zu verbieten.
5. **Fairness** über `rotation_state`: Wer nie im Fokus war, bekommt Bonus; wer
   gestern dran war, Abzug. Verhindert immer dieselben drei Gewinner.
6. **Auswahl** (`dashboard_service.build_cockpit`): aus allen Kandidaten werden
   maximal drei sichtbar. Der Rest bleibt in der Engine, nicht auf dem Schirm.

## Oberfläche


Der Einstieg ist der Einfachmodus: **Heute**, **Kontakte**, **Einstellungen**.
Der Expertenmodus (Strg+E) blendet zusätzlich **Rotation** ein – die einzige
Ansicht, in der die Punktzahl sichtbar wird.

Das Cockpit zeigt vier Kacheln (responsiv 4 / 2 / 1 Spalten) und darunter
höchstens drei Vorschlagskarten. Jede Karte hat genau eine Hauptaktion
(*Getroffen* / *Angerufen* / *Geschrieben*), die mit **einem Klick ohne
Rückfrage** in die Datenbank schreibt – die Kontaktart steht ja bereits fest,
weil die Engine sie vorgeschlagen hat. Daneben *Planen*, *Später* (mit
Snooze-Auswahl) und der Sprung zum Kontakt. „Warum?" klappt die Begründung auf.

Ist nichts fällig, verschwindet die Liste und es erscheint eine einzelne
Entwarnungskarte. Leere Bereiche werden ausgeblendet statt leer angezeigt.

Dringlichkeit wird über einen farbigen Punkt und den farbigen Kartenrand
transportiert, nicht über Emoji: Zeichen wie U+1F7E0 fehlen in vielen
Systemschriften und erscheinen dort als leere Lücke.

## Struktur


```
freizeitmanager/
├── paths.py                     Datenpfade, Host-Vorgabe hat Vorrang
├── database/
│   ├── models.py                Kontakte, Interaktionen, Rotation, Aktivitäten
│   └── db.py                    Session, Schemaversion, Standardwerte, Backup
├── logic/
│   ├── freshness.py             Beziehungsfrische
│   ├── rule_engine.py           harte Regeln + Kapazität
│   ├── rotation_engine.py       Score, Begründung, Fairness, Snooze
│   ├── contact_service.py       Kontakte, Interaktionen, Termine, Quick Actions
│   └── dashboard_service.py     Fokus-Cockpit, Reroll, Energiezustand
├── ui/
│   ├── theme_manager.py         Profile, eigene Fassungen, gemeinsames Theme
│   └── profiles/*.json          9 mitgelieferte Themes
├── i18n/
│   ├── translator.py            t(), Sprachwahl, Datum und Wochentage
│   └── de.json / en.json / fr.json
├── integration/
│   ├── lifeplanner_bridge.py    JSONL-Outbox nach lifeplanner.module.v1
│   └── legacy_import.py         Übernahme aus termine.db
└── ui/
    ├── main_window.py           Sidebar, Einfach-/Expertenmodus
    ├── dashboard_widget.py      Fokus-Cockpit
    ├── contacts_widget.py       Kontaktliste mit Rotationszustand
    ├── rotation_widget.py       vollständige Bewertung (Expertenbereich)
    ├── settings_widget.py       Kapazität, Fokus, LifePlanner
    ├── common.py                Kachel, Vorschlagskarte, Ruhezustand
    ├── dialogs.py               Kontakt, Termin, Kontakt nachtragen
    └── styles.py / theme.py     Stylesheet und Farbkonstanten
```

## Themes


Zwei Rückfallprofile stecken im Code, alles Weitere liegt als JSON in
`freizeitmanager/ui/profiles`. Eigene Fassungen landen im Datenordner unter
`theme_profiles/` und überschreiben das mitgelieferte Profil, ohne es zu
zerstören. Ein fehlerhaftes Profil wird übersprungen, in
`logs/theme_profile_errors.log` protokolliert und in den Einstellungen
gemeldet – die Anwendung startet trotzdem.

Außerhalb der Profildateien enthält die Oberfläche keinen einzigen festen
Farbwert.

### Ein Theme für alle Module

Der Haken **„Für alle LifePlanner-Module übernehmen"** schreibt das Theme nach
`$LIFEPLANNER_BRIDGE_DIR/shared_theme.json` (Schema `lifeplanner.theme.v1`).
Andere Module lesen es dort, solange sie **„Gemeinsames Theme des LifePlanners
übernehmen"** eingeschaltet haben. Der Austausch läuft über den Bridge-Ordner,
weil der Modul-Host-Vertrag den Zugriff auf fremde Datenbanken verbietet.

Das Format und die drei Regeln stehen in `docs/GEMEINSAMES_THEME.md`.

## LifePlanner-Integration


Nach `Liveplanner/docs/MODUL_HOST_VERTRAG.md` v1:

* Das Modul läuft in einem **eigenen Prozess**. Der Host importiert keine
  Fachlogik, das Modul öffnet **keine fremde Datenbank**.
* Der Datenordner kommt über `FREIZEITMANAGER_DATA_DIR` bzw.
  `LIFEPLANNER_MODULE_DATA_DIR`. Ohne Host liegt er neben dem Programm –
  **nie** im zufälligen Arbeitsverzeichnis.
* Der Austausch läuft über eine versionierte, **atomar** geschriebene Datei
  `$LIFEPLANNER_BRIDGE_DIR/freizeitmanager_to_lifeplanner.jsonl`
  (Schema `freizeitmanager.focus.v1`). Sie enthält nur Ergebnisse – Zählwerte
  und die nächsten Schritte –, niemals Notizen oder Rohdaten.
* Fachevents (`freizeit.interaction.logged`, `freizeit.focus.changed`,
  `freizeit.plan.created`, `freizeit.plan.completed`) gehen als
  `lifeplanner.event.v1` nach `events/events.jsonl`.

Ohne gesetzte Host-Variablen sind Bridge und Events stille No-Ops –
der FreizeitManager läuft vollständig standalone.

## Prüfwerkzeuge

`ruff` entscheidet über Releases. Es ist darum exakt gepinnt — eine neue
Nebenversion bringt neue Regeln mit und macht einen Lauf rot, ohne dass sich
eine Zeile Code geändert hätte.

Damit lokal dasselbe gilt wie in der CI, nicht direkt aufrufen, sondern:

```bash
python3 tools/gepinnte_werkzeuge.py ruff check .
```

Das Skript fährt die Version aus `requirements-build.txt` in einer eigenen
Umgebung. Ohne es urteilt die Version, die gerade im PATH liegt.

## Release


Die Version steht nur in `version.json`; `app_info.py` und `module.json` werden
daraus abgeleitet:

```bash
python3 tools/sync_version.py            # ableiten
python3 tools/sync_version.py --check    # nur prüfen, schreibt nichts
```

Ein Tag `v*` löst die Pipeline aus. Sie prüft zuerst (Tag und Version müssen
übereinstimmen, Linting, Tests, GUI-Rauchtest), baut dann mit PyInstaller auf
Linux und Windows und veröffentlicht zuletzt zwei `.lpmodule`-Pakete samt
Prüfsummen. Gebaut wird nur, was geprüft wurde; veröffentlicht wird nur, was
`tools/verify_lpmodule.py` akzeptiert.

Lokal von Hand:

```bash
python3 -m PyInstaller FreizeitManager.spec --noconfirm --clean
QT_QPA_PLATFORM=offscreen ./dist/FreizeitManager/FreizeitManager --smoke
python3 tools/build_lifeplanner_module.py \
  --runtime-dir dist/FreizeitManager --runtime-name FreizeitManager \
  --platform linux-x86_64 --output-dir dist --allow-unsigned
python3 tools/verify_lpmodule.py dist/freizeitmanager_*.lpmodule
```

Das Paketformat folgt `lifeplanner_core/module_installer.py`: `component.json`
im Schema `lifeplanner.component.v1`, ein `payload/`-Verzeichnis und ein
`payload_sha256` über genau diesen Baum. Das Ausführbit des deklarierten
Programms wird direkt ins Archiv geschrieben – CI-Artefakte verlieren Unix-Rechte,
und das Linux-Paket kann auf einem Windows-Runner entstehen. Ohne das startet
das installierte Modul mit „[Errno 13] Keine Berechtigung“.

Signatur (Ed25519) ist vorbereitet und optional. Ohne Schlüssel entstehen
sichtbar unsignierte Pakete; mit hinterlegtem `FREIZEITMANAGER_SIGNING_KEY`
wird `component.json` signiert und die Signatur vor dem Hochladen geprüft.

## Was aus dem alten Kontaktmanager übernommen wurde


`termine.db` enthielt **keine Kontakte**, aber gepflegte Gruppen,
Beziehungsgrade und Kapazitätseinstellungen. `integration/legacy_import.py`
übernimmt sie und löst dabei die Freitextreferenzen in echte Datensätze auf.
Wäre ein Kontakt vorhanden, würde `letztes_treffen` zur ersten Interaktion
seiner Historie.

Der alte Code liegt unverändert daneben (`main.py`, `db.py`,
`Kontaktmanager_ui.py`, `README_kontaktmanager_alt.md`) und wird von nichts
Neuem mehr benutzt.
