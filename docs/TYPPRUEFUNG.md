# Typprüfung im FreizeitManager — Stand und Weg

BudgetManager und LifePlanner werden seit Loop 55/57 mit `mypy` geprüft. Der
FreizeitManager noch nicht. Diese Datei hält fest, warum, und was dafür nötig
wäre — damit der nächste Anlauf nicht bei null anfängt.

## Der Befund

Ein Lauf über `freizeitmanager/` meldet **84 Fehler**. Sie haben fast alle
dieselbe Wurzel:

| Art | Zahl | Ursache |
|---|---|---|
| `var-annotated` | 36 | Spalten in `database/models.py` ohne Typ |
| `[str]`, `[int]`, `[date]` | 31 | Folgefehler: Attributtypen sind unbekannt |
| `attr-defined` | 8 | teils echte Funde, teils Qt-Typisierung |
| Rest | 9 | Einzelfälle |

**Die Wurzel ist eine Datei.** `database/models.py` deklariert 62 Spalten in
der alten SQLAlchemy-Schreibweise:

```python
contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
```

SQLAlchemy 2.0 kennt dafür die typisierte Form:

```python
contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"))
```

Beide erzeugen dasselbe Schema. Nur die zweite sagt mypy, welchen Typ das
Attribut hat — und ohne diese Angabe weiß es an jeder Verwendungsstelle
nichts, daher die 31 Folgefehler.

## Warum das ein eigener Schritt ist

Es sind 62 Zeilen, und jede trägt eine Entscheidung: `nullable=True` wird zu
`Mapped[X | None]`, ein `default` wandert, eine Beziehung braucht
`Mapped[list[...]]`. Ein falsch abgeleiteter Typ ändert nichts am Schema, aber
er beschreibt dann etwas anderes, als tatsächlich in der Spalte steht — und
das fällt erst auf, wenn jemand sich darauf verlässt.

Der Umbau gehört darum in einen Schritt, in dem das Programm auch bedient
werden kann, nicht nebenbei.

## Was schon sauber ist

Diese Module haben null Fehler und hängen nicht am Datenmodell:

`atomic_write.py`, `defensive_log.py`, `file_permissions.py`, `paths.py`,
`app_info.py`, `integration/lifeplanner_events.py`

Ein Gate über nur diese sechs wäre allerdings Symbolpolitik — es würde nichts
prüfen, was heute schiefgehen kann.

## Die echten Funde, die der Lauf schon gebracht hat

Zwei sind in Loop 58 behoben:

- **`theme_manager.py`**: `QGuiApplication.instance().styleHints()` — der Umweg
  über `instance()` war länger und zwang zu einer `None`-Prüfung, die nichts
  sicherer macht. `styleHints()` ist statisch. Dieselbe Stelle gab es im
  LifePlanner (Loop 57).
- **`rule_engine.py`**: Vier Schleifen über zwei verschiedene Tabellen, alle
  mit der Variablen `row`. Kein Fehler, aber wer die Stelle liest, musste
  zurückblättern, um zu wissen, was gerade gemeint ist.
