"""Der FreizeitManager meldet dem Host, wer gerade dran wäre.

Das Schema ``lifeplanner.notice.v1`` stammt aus genau diesem Modul: Es schrieb
solche Meldungen als einziges, nur in einem eigenen Format. Seit Loop 47 lesen
alle Module dasselbe; Loop 48 hängt den FreizeitManager daran.

Der wichtigste Test hier ist der über die Dringlichkeit: Eine still gewordene
Freundschaft darf im Dashboard **keine rote Meldung** werden. Das Programm ist
ausdrücklich so gebaut, dass es keinen Schuldenberg aufbaut — eine Alarmstufe
im Host würde genau das wieder einführen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from freizeitmanager.integration.lifeplanner_notices import (
    DRINGLICHKEITEN,
    HOECHSTZAHL,
    MANIFEST_SCHEMA,
    NOTICE_SCHEMA,
    NOTICES_FILE,
    STUFEN,
    Meldung,
    aus_cockpit,
    kennung,
)
from freizeitmanager.logic.rotation_engine import (
    URGENCY_DUE,
    URGENCY_FRESH,
    URGENCY_LONG,
    URGENCY_SOON,
)


@dataclass
class _Kandidat:
    contact_id: int = 1
    name: str = "Anna"
    urgency: str = URGENCY_DUE
    suggestion: str = "call"

    def headline(self) -> str:
        return f"{self.name} \N{MIDDLE DOT} jetzt ein guter Zeitpunkt"

    @property
    def suggestion_text(self) -> str:
        return "Anrufen"


@dataclass
class _Cockpit:
    next_steps: list = field(default_factory=list)


def test_faelliger_kontakt_wird_zur_meldung() -> None:
    (meldung,) = aus_cockpit(_Cockpit([_Kandidat()]))
    assert meldung.dringlichkeit == "info"
    assert "Anna" in meldung.ueberschrift
    assert meldung.zusatz == "Anrufen"
    assert meldung.bereich == "rotation"


def test_frischer_kontakt_meldet_nichts() -> None:
    """Wer gerade erst Kontakt hatte, ist keine Meldung."""
    assert aus_cockpit(_Cockpit([_Kandidat(urgency=URGENCY_FRESH)])) == []


def test_lange_stille_ist_hoechstens_eine_warnung() -> None:
    """Kein Schuldenberg - auch nicht im Dashboard des Hosts.

    Eine Freundschaft, die still geworden ist, ist kein Alarm. Würde sie
    hier "kritisch", stünde sie im Host neben einem überzogenen Budget -
    und genau dieses Gefühl will das Programm nicht erzeugen.
    """
    (meldung,) = aus_cockpit(_Cockpit([_Kandidat(urgency=URGENCY_LONG)]))
    assert meldung.dringlichkeit == "warnung"
    assert "kritisch" not in {m for m in STUFEN.values()}


def test_keine_stufe_wird_kritisch() -> None:
    assert "kritisch" not in STUFEN.values()


def test_alle_bekannten_stufen_sind_zugeordnet() -> None:
    """Bis auf ``fresh``, das bewusst fehlt."""
    assert set(STUFEN) == {URGENCY_LONG, URGENCY_DUE, URGENCY_SOON}
    assert URGENCY_FRESH not in STUFEN


def test_die_zahl_der_meldungen_ist_gedeckelt() -> None:
    """Das Cockpit zeigt selbst höchstens drei - mehr wäre mehr Druck."""
    assert HOECHSTZAHL == 3


def test_kennung_ist_stabil_und_kein_klartext() -> None:
    a = kennung("next_step", 7)
    b = kennung("next_step", 7)
    c = kennung("next_step", 8)
    assert a == b != c
    assert "next_step" not in a


def test_meldung_ohne_ueberschrift_wird_abgelehnt() -> None:
    with pytest.raises(ValueError):
        Meldung(kennung="x", dringlichkeit="info", ueberschrift=" ")


def test_unbekannte_dringlichkeit_wird_abgelehnt() -> None:
    with pytest.raises(ValueError):
        Meldung(kennung="x", dringlichkeit="dringend", ueberschrift="Probe")


# ── Kontrakt gegen den Host ───────────────────────────────────────────────


def test_zeile_passt_zum_host_schema() -> None:
    """Die Feldnamen sind der Vertrag.

    Schreib- und Leseseite liegen in verschiedenen Repositories. Wer hier
    ``ueberschrift`` statt ``headline`` schreibt, merkt es erst, wenn das
    Dashboard leer bleibt - und das sieht aus wie "es ist nichts los".
    """
    (meldung,) = aus_cockpit(_Cockpit([_Kandidat()]))
    zeile = meldung.als_zeile()
    assert set(zeile) == {"schema", "id", "urgency", "headline", "detail", "area"}
    assert zeile["schema"] == "lifeplanner.notice.v1"
    assert zeile["urgency"] in DRINGLICHKEITEN
    # Muss sich als JSON schreiben lassen, sonst bricht der Lauf erst
    # beim Nutzer.
    json.loads(json.dumps(zeile))


def test_der_dateiname_passt_zum_suchmuster_des_hosts() -> None:
    assert NOTICES_FILE.endswith("_notices.jsonl")


def test_schemata_stimmen_mit_dem_host_ueberein() -> None:
    assert MANIFEST_SCHEMA == "lifeplanner.notice.manifest.v1"
    assert NOTICE_SCHEMA == "lifeplanner.notice.v1"
    assert DRINGLICHKEITEN == ("info", "warnung", "kritisch")


def test_ohne_host_wird_nichts_geschrieben(monkeypatch) -> None:
    """Standalone ist die Bridge ein No-Op - so steht es im Vertrag."""
    from freizeitmanager import paths
    from freizeitmanager.integration import lifeplanner_notices as ln

    monkeypatch.setattr(paths, "bridge_dir", lambda: None)
    assert ln.publish_notices(_Cockpit([_Kandidat()])) is None


def test_meldungen_tragen_keine_notizen() -> None:
    """Nur Ergebnisse - keine privaten Aufzeichnungen über andere Menschen."""
    (meldung,) = aus_cockpit(_Cockpit([_Kandidat()]))
    inhalt = json.dumps(meldung.als_zeile()).lower()
    for verboten in ("note", "notiz", "birthday", "geburtstag", "interaction"):
        assert verboten not in inhalt
