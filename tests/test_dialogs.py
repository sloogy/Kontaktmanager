"""Dialoge wirklich aufbauen - in jeder angebotenen Sprache.

Diese Tests fehlten und die Luecke war teuer: In ``dialogs.py`` war ``t``
zeitweise gar nicht importiert. Kein Test hat je einen Dialog geoeffnet,
also fiel es nicht auf - ein Klick auf "Neuer Kontakt" haette die Anwendung
mit einem NameError begruesst.
"""
from __future__ import annotations

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from freizeitmanager.i18n.translator import LANGUAGES, set_language
from freizeitmanager.logic import contact_service as cs


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _german_again():
    yield
    set_language("de")


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_kontaktdialog_baut_in_jeder_sprache_auf(qapp, session, lang):
    from freizeitmanager.ui.dialogs import ContactDialog
    set_language(lang)
    dialog = ContactDialog(["Familie", "Freund"], ["Freunde", "Arbeit"])
    values = dialog.values()
    # Die Schluessel sind sprachunabhaengig - nur die Beschriftung wechselt.
    assert set(values) >= {"name", "importance", "target_interval_days", "status", "tags"}
    assert values["importance"] == 3
    assert dialog.windowTitle()
    assert "contact." not in dialog.windowTitle(), "unaufgeloester Schluessel"


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_interaktionsdialog_baut_in_jeder_sprache_auf(qapp, session, lang):
    from freizeitmanager.ui.dialogs import LogInteractionDialog
    set_language(lang)
    dialog = LogInteractionDialog("Marko")
    values = dialog.values()
    assert values["kind"] == "meet"
    assert values["occurred_on"] == date.today()
    assert "Marko" in dialog.windowTitle()
    assert dialog.kind.count() == 7
    labels = [dialog.kind.itemText(i) for i in range(dialog.kind.count())]
    assert all(label and "interaction." not in label for label in labels)


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_planungsdialog_baut_in_jeder_sprache_auf(qapp, session, lang):
    from freizeitmanager.ui.dialogs import PlanActivityDialog
    set_language(lang)
    dialog = PlanActivityDialog([(1, "Marko"), (2, "Nadine")], {1})
    values = dialog.values()
    assert values["contact_ids"] == [1]
    assert values["title"]
    assert "activity." not in values["title"]


def test_bearbeiten_uebernimmt_die_werte_des_kontakts(qapp, session):
    """Der Bearbeiten-Weg ist ein anderer Codepfad als das Anlegen."""
    from freizeitmanager.ui.dialogs import ContactDialog
    contact = cs.create_contact(session, "Marko", importance=5,
                                target_interval_days=21, groups=["Freunde"],
                                tags=["Brettspiele"])
    session.commit()

    dialog = ContactDialog(["Familie"], ["Freunde", "Arbeit"], contact=contact)
    values = dialog.values()
    assert values["name"] == "Marko"
    assert values["importance"] == 5
    assert values["target_interval_days"] == 21
    assert values["groups"] == ["Freunde"]
    assert values["tags"] == ["Brettspiele"]


def test_leerer_name_wird_nicht_angenommen(qapp, session):
    from freizeitmanager.ui.dialogs import ContactDialog
    dialog = ContactDialog([], [])
    dialog.name.setText("   ")
    dialog._accept_if_valid()
    assert dialog.result() != ContactDialog.DialogCode.Accepted
