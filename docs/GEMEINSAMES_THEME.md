# Gemeinsames Theme für LifePlanner-Module

**Schema:** `lifeplanner.theme.v1`
**Ort:** `$LIFEPLANNER_BRIDGE_DIR/shared_theme.json`

## Warum eine Datei und keine geteilte Einstellung

Der Modul-Host-Vertrag (`Liveplanner/docs/MODUL_HOST_VERTRAG.md`) verbietet den
Zugriff auf fremde Datenbanken. Ein Modul darf die Einstellungen eines anderen
weder lesen noch schreiben. Ein gemeinsames Erscheinungsbild kann deshalb nur
über eine versionierte Datei im Bridge-Ordner des Profils entstehen — genau wie
jeder andere modulübergreifende Austausch.

## Die drei Regeln

1. **Lesen ist freiwillig.** Ein Modul übernimmt das gemeinsame Theme nur, wenn
   der Nutzer das dort eingeschaltet hat (`ui.theme_follow_shared`). Andernfalls
   gilt die lokale Wahl.
2. **Schreiben ist eine ausdrückliche Handlung.** Nur wer „Für alle
   LifePlanner-Module übernehmen" anhakt, verändert die Datei. Ein Modul, das
   beim Start ungefragt sein Theme veröffentlicht, würde die Wahl aller anderen
   überschreiben.
3. **Ohne Host passiert nichts.** Fehlt `LIFEPLANNER_BRIDGE_DIR`, sind alle
   Funktionen stille No-Ops und die Bedienelemente ausgegraut.

## Format

```json
{
  "schema": "lifeplanner.theme.v1",
  "name": "Nord - Dunkel",
  "modus": "dunkel",
  "schriftgroesse": 14,
  "farben": {
    "hintergrund_app": "#2e3440",
    "text": "#eceff4",
    "akzent": "#88c0d0"
  },
  "gesetzt_von": "freizeitmanager",
  "modul_version": "0.1.3",
  "profil": "default",
  "geaendert_am": "2026-08-20T12:00:00+00:00"
}
```

| Feld | Bedeutung |
|---|---|
| `schema` | Muss `lifeplanner.theme.v1` sein. Abweichendes Schema → Datei ignorieren. |
| `name` | Anzeigename des Themes. Pflichtfeld. |
| `modus` | `hell` oder `dunkel`. Erlaubt einem Modul die grobe Anpassung, auch wenn es die Farben nicht kennt. |
| `schriftgroesse` | Punktgröße, 8–22. |
| `farben` | Vollständiger Farbauszug. Ein Modul, das dieses Theme selbst mitliefert, benutzt **seine eigene Fassung** — sie ist vollständiger. |
| `gesetzt_von` | Modul-ID, die zuletzt geschrieben hat. Nur zur Anzeige. |

## Verhalten beim Lesen

```
Kennt das Modul ein Profil mit diesem Namen?
├── ja   → eigenes Profil benutzen (vollständig)
└── nein → aus "farben" + "modus" ein Profil bauen
             └── ungültig? → gemeinsames Theme ignorieren, lokal bleiben
```

Eine beschädigte oder fremdschematische Datei darf **nie** dazu führen, dass ein
Modul farblos oder gar nicht startet. Sie wird protokolliert und ignoriert.

## Schreiben

Atomar: erst `shared_theme.json.tmp`, dann `replace()`. Ein anderes Modul darf
nie eine halbe Datei lesen.

## Umsetzungsstand

| Modul | Liest | Schreibt |
|---|---|---|
| FreizeitManager | ja | ja |
| BudgetManager | offen | offen |
| FPM | offen | offen |
| LifePlanner (Host) | offen | offen |

Die Referenzumsetzung steht in
`freizeitmanager/integration/shared_theme.py` (rund 110 Zeilen, ohne
Qt-Abhängigkeit) und kann übernommen werden. Für ein Modul sind nur zwei
Berührungspunkte nötig: beim Aufbau des Themes `read_shared_theme()` befragen
und beim Anhaken der Sammeloption `publish_shared_theme()` aufrufen.
