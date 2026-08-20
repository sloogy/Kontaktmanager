# FreizeitManager

Freundschaftspflege, Kontaktrotation und Freizeitplanung – als eigenständiges
Programm und als LifePlanner-Modul.

Der FreizeitManager beantwortet nicht „wann habe ich wen zuletzt gesehen?",
sondern **„was wäre jetzt eine gute, realistische Aktion für mich?"**

## Stand

| Bereich | Stand |
|---|---|
| Datenmodell, Migrationen, Pfadverwaltung | fertig |
| Beziehungsfrische (`logic/freshness.py`) | fertig |
| Regel- und Kapazitäts-Engine (`logic/rule_engine.py`) | fertig |
| Rotation Engine (`logic/rotation_engine.py`) | fertig |
| Fokus-Cockpit-Service (`logic/dashboard_service.py`) | fertig |
| LifePlanner-Bridge + Legacy-Import (`integration/`) | fertig |
| Qt-Oberfläche: Cockpit, Kontakte, Rotation, Einstellungen | fertig |
| Release-Pipeline: CI, Build, `.lpmodule`, Verifizierer | fertig |
| Tests | 49, grün (UI- und Paketierungstests inbegriffen) |
| Hobbys / Aktivitäten (0.2) | offen |
| Kalenderzugriff (0.3) | architektonisch vorgesehen, nicht gebaut |

Start: `python3 main.py`
Kontrolllauf ohne Qt: `python3 tools/demo_cockpit.py`
Tests: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q`
Rauchtest: `python3 tools/gui_smoke_test.py`

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

### Warum die Frische kein Datum ist

```
Treffen vor 42 Tagen, Ziel 21 Tage                   → überfällig (Faktor 2,2)
… plus Emoji von gestern                             → immer noch überfällig (1,9)
… plus langes Telefonat vor 3 Tagen                  → nicht mehr fällig (0,15)
```

Ein „Happy Birthday 🎂" darf einen engen Freund nicht für 30 Tage aus der
Rotation nehmen. Deshalb hat jede Kontaktart eine eigene Grundwirkung
(`freshness.BASE_WEIGHTS`), und Nachrichten/Reaktionen lösen weder eine
Sperrfrist aus noch gelten sie als „letzter Kontakt".

Frische über 1,0 ist **Guthaben**: Nach einem intensiven gemeinsamen Wochenende
ist der nächste Kontakt später fällig als nach einem Kaffee.

### Kein Schuldenberg

Wer die App drei Wochen nicht öffnet, sieht danach nicht „🔴 17 überfällige
Freundschaften", sondern drei sinnvolle nächste Schritte und den Satz
*„Schön, dass du wieder da bist."* Die anderen vierzehn bleiben intern
bewertet, aber unsichtbar.

Nach außen gibt die Engine nie eine Punktzahl aus, sondern eine
Dringlichkeitsstufe, eine Empfehlung und lesbare Gründe (`Candidate.why()`).
Die Punktzahl existiert nur im `breakdown` für den Expertenmodus.

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

## Was aus dem alten Kontaktmanager übernommen wurde

`termine.db` enthielt **keine Kontakte**, aber gepflegte Gruppen,
Beziehungsgrade und Kapazitätseinstellungen. `integration/legacy_import.py`
übernimmt sie und löst dabei die Freitextreferenzen in echte Datensätze auf.
Wäre ein Kontakt vorhanden, würde `letztes_treffen` zur ersten Interaktion
seiner Historie.

Der alte Code liegt unverändert daneben (`main.py`, `db.py`,
`Kontaktmanager_ui.py`, `README_kontaktmanager_alt.md`) und wird von nichts
Neuem mehr benutzt.
