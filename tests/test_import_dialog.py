"""Die Vorschau des Imports - aufgebaut wie im Betrieb, in jeder Sprache.

Der Dialog ist der einzige Ort, an dem ueber bestehende Kontakte entschieden
wird. Ein Fehler hier wuerde Daten ueberschreiben, die niemand freigegeben hat.
"""
from __future__ import annotations

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from pathlib import Path

from PySide6.QtWidgets import QApplication

from freizeitmanager.i18n.translator import LANGUAGES, set_language
from freizeitmanager.logic import contact_import as imp
from freizeitmanager.logic import contact_service as cs

HEADERS = ["Name", "Geburtstag", "Gruppe"]
ROWS = [
    ["Anna Weber", "01.02.1990", "Freunde"],
    ["Marko", "05.06.", "Sport"],          # Name existiert schon -> Konflikt
    ["Bert Falsch", "irgendwann", ""],     # unlesbares Datum, aber brauchbar
    ["", "01.01.1980", ""],                # ohne Namen -> unbrauchbar
]


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _german_again():
    yield
    set_language("de")


@pytest.fixture()
def preview():
    return imp.build_preview(HEADERS, [list(r) for r in ROWS], existing={"marko": 1})


def test_vorschau_trennt_neue_von_bestehenden(preview):
    assert [r.name for r in preview.new_rows] == ["Anna Weber", "Bert Falsch"]
    assert [r.name for r in preview.conflicts] == ["Marko"]
    assert [r.line for r in preview.unusable] == [5]


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_dialog_baut_in_jeder_sprache_auf(qapp, session, preview, lang):
    from freizeitmanager.ui.import_dialog import ImportPreviewDialog
    set_language(lang)
    dialog = ImportPreviewDialog(preview, Path("liste.csv"))
    # Unbrauchbare Zeilen stehen nicht in der Tabelle - an ihnen gibt es
    # nichts zu entscheiden.
    assert dialog._table.rowCount() == 3
    texts = [dialog._table.item(r, c).text()
             for r in range(dialog._table.rowCount())
             for c in range(4)]
    assert all("import." not in text for text in texts), texts
    labels = [dialog._combos[0].itemText(i) for i in range(dialog._combos[0].count())]
    assert all(label and "import." not in label for label in labels)
    assert dialog.actions_for(0), "Aktionen muessen echte RowAction-Werte sein"


def test_bestehender_kontakt_kann_nicht_angelegt_werden(qapp, session, preview):
    """Fuer einen Konflikt darf 'Anlegen' gar nicht erst zur Wahl stehen."""
    from freizeitmanager.ui.import_dialog import ImportPreviewDialog
    dialog = ImportPreviewDialog(preview, Path("liste.csv"))
    conflict = next(i for i, row in enumerate(dialog._rows) if row.is_conflict)
    actions = dialog.actions_for(conflict)
    assert imp.RowAction.CREATE not in actions
    assert set(actions) == {imp.RowAction.SKIP, imp.RowAction.FILL}
    assert not dialog.set_action(conflict, imp.RowAction.CREATE)
    # Und die Vorauswahl ruehrt den bestehenden Kontakt nicht an.
    assert dialog.action_at(conflict) is imp.RowAction.SKIP


def test_neue_zeile_ist_zum_anlegen_vorgewaehlt(qapp, session, preview):
    from freizeitmanager.ui.import_dialog import ImportPreviewDialog
    dialog = ImportPreviewDialog(preview, Path("liste.csv"))
    new_index = next(i for i, row in enumerate(dialog._rows) if not row.is_conflict)
    assert dialog.action_at(new_index) is imp.RowAction.CREATE


def test_entscheidungen_landen_in_der_vorschau(qapp, session, preview):
    from freizeitmanager.ui.import_dialog import ImportPreviewDialog
    dialog = ImportPreviewDialog(preview, Path("liste.csv"))
    conflict = next(i for i, row in enumerate(dialog._rows) if row.is_conflict)
    assert dialog.set_action(conflict, imp.RowAction.FILL)
    decided = dialog.decided_preview()
    assert next(r for r in decided.rows if r.is_conflict).action is imp.RowAction.FILL
    # Die unbrauchbare Zeile bleibt unberuehrt auf SKIP.
    assert all(r.action is imp.RowAction.SKIP for r in decided.unusable)


def test_sammelaktion_wirkt_nur_auf_bestehende(qapp, session, preview):
    from freizeitmanager.ui.import_dialog import ImportPreviewDialog
    dialog = ImportPreviewDialog(preview, Path("liste.csv"))
    dialog._set_all_conflicts(imp.RowAction.FILL)
    decided = dialog.decided_preview()
    assert all(r.action is imp.RowAction.FILL for r in decided.conflicts)
    assert all(r.action is imp.RowAction.CREATE for r in decided.new_rows)


def test_ohne_freigabe_bleibt_der_knopf_aus(qapp, session, preview):
    from freizeitmanager.ui.import_dialog import ImportPreviewDialog
    dialog = ImportPreviewDialog(preview, Path("liste.csv"))
    assert dialog._ok.isEnabled()
    for index in range(len(dialog._combos)):
        assert dialog.set_action(index, imp.RowAction.SKIP)
    assert not dialog._ok.isEnabled()


def test_unlesbares_datum_wird_im_klartext_gemeldet(qapp, session, preview):
    """Der Befund traegt den Rohwert - sonst weiss niemand, welche Zelle."""
    from freizeitmanager.ui.import_dialog import ImportPreviewDialog
    dialog = ImportPreviewDialog(preview, Path("liste.csv"))
    index = next(i for i, row in enumerate(dialog._rows) if row.name == "Bert Falsch")
    assert "irgendwann" in dialog._table.item(index, 3).text()


def test_geburtstag_ohne_jahrgang_zeigt_kein_jahr(qapp, preview):
    from freizeitmanager.ui.import_dialog import birthday_text
    row = next(r for r in preview.rows if r.name == "Marko")
    assert row.birthday_has_year is False
    assert "1900" not in birthday_text(row)
    assert "05.06." == birthday_text(row)


def test_import_schreibt_genau_die_freigegebenen_zeilen(qapp, session, preview):
    """Der ganze Weg: Vorschau, Entscheidung, Schreiben."""
    from freizeitmanager.database.models import Contact
    from freizeitmanager.ui.import_dialog import ImportPreviewDialog
    marko = cs.create_contact(session, "Marko")
    session.commit()

    live = imp.build_preview(HEADERS, [list(r) for r in ROWS],
                             existing=imp.existing_names(session))
    dialog = ImportPreviewDialog(live, Path("liste.csv"))
    conflict = next(i for i, row in enumerate(dialog._rows) if row.is_conflict)
    assert dialog.set_action(conflict, imp.RowAction.FILL)

    result = imp.apply_preview(session, dialog.decided_preview())
    session.commit()

    assert result.created == 2
    assert result.filled == 1
    names = {c.name for c in session.query(Contact)}
    assert names == {"Marko", "Anna Weber", "Bert Falsch"}
    assert session.get(Contact, marko.id).birthday == date(imp.YEAR_UNKNOWN, 6, 5)
    assert session.get(Contact, marko.id).birthday_has_year is False
    assert next(c for c in session.query(Contact) if c.name == "Anna Weber").birthday == date(1990, 2, 1)
