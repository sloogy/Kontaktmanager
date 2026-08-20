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
