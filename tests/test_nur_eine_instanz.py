"""Nur eine Instanz je Datenordner.

Zwei Instanzen auf demselben Datenordner sind kein theoretisches Problem: Die
zweite liest den Stand beim Start, die erste schreibt weiter, und wer zuletzt
speichert gewinnt. Der Nutzer merkt es erst, wenn Eintraege verschwunden sind.

Alle vier Programme der Suite fuehren diesen Test unter demselben Namen.
"""

from __future__ import annotations

import json
import os

import pytest

from freizeitmanager.single_instance import SingleInstanceGuard, is_pid_alive


def test_die_erste_instanz_bekommt_die_sperre(tmp_path):
    guard = SingleInstanceGuard(tmp_path / "lock", app_id="Probe")
    frei, grund = guard.acquire()
    assert frei and grund == ""
    guard.release()


def test_die_zweite_instanz_wird_abgewiesen(tmp_path):
    erste = SingleInstanceGuard(tmp_path / "lock", app_id="Probe")
    assert erste.acquire()[0]
    try:
        zweite = SingleInstanceGuard(tmp_path / "lock", app_id="Probe")
        frei, grund = zweite.acquire()
        assert not frei
        assert str(os.getpid()) in grund, grund
    finally:
        erste.release()


def test_nach_dem_freigeben_geht_es_wieder(tmp_path):
    erste = SingleInstanceGuard(tmp_path / "lock", app_id="Probe")
    erste.acquire()
    erste.release()

    zweite = SingleInstanceGuard(tmp_path / "lock", app_id="Probe")
    assert zweite.acquire()[0]
    zweite.release()


def test_eine_sperre_nach_absturz_wird_uebernommen(tmp_path):
    """Der wichtige Fall: Nach einem Absturz bleibt die Sperre liegen. Wuerde
    sie nicht uebernommen, kaeme der Nutzer nie wieder in sein Programm."""
    lock = tmp_path / "lock"
    lock.mkdir()
    # PID, die es mit an Sicherheit grenzender Wahrscheinlichkeit nicht gibt.
    (lock / "pid").write_text("999999", encoding="utf-8")

    guard = SingleInstanceGuard(lock, app_id="Probe")
    frei, grund = guard.acquire()
    assert frei, grund
    assert (lock / "pid").read_text(encoding="utf-8") == str(os.getpid())
    guard.release()


@pytest.mark.parametrize("inhalt", ["", "keine zahl", "-1", "0"])
def test_eine_kaputte_pid_datei_blockiert_nicht(tmp_path, inhalt):
    """Sonst haette ein halb geschriebenes Lock den Start dauerhaft verhindert."""
    lock = tmp_path / "lock"
    lock.mkdir()
    (lock / "pid").write_text(inhalt, encoding="utf-8")

    guard = SingleInstanceGuard(lock, app_id="Probe")
    assert guard.acquire()[0]
    guard.release()


def test_die_sperre_verraet_wer_sie_haelt(tmp_path):
    """Fuer die Fehlersuche: Wer haengt da noch?"""
    guard = SingleInstanceGuard(tmp_path / "lock", app_id="Probe")
    guard.acquire()
    try:
        besitzer = json.loads((tmp_path / "lock" / "owner.json").read_text(encoding="utf-8"))
        assert besitzer["app_id"] == "Probe"
        assert besitzer["pid"] == os.getpid()
    finally:
        guard.release()


def test_getrennte_datenordner_stoeren_sich_nicht(tmp_path):
    """Gesperrt wird der Datenordner, nicht das Programm."""
    eins = SingleInstanceGuard(tmp_path / "a" / "lock", app_id="Probe")
    zwei = SingleInstanceGuard(tmp_path / "b" / "lock", app_id="Probe")
    assert eins.acquire()[0]
    assert zwei.acquire()[0]
    eins.release()
    zwei.release()


def test_release_raeumt_nur_die_eigene_sperre(tmp_path):
    """Ein Guard, der nie erworben hat, darf nichts wegraeumen."""
    lock = tmp_path / "lock"
    erste = SingleInstanceGuard(lock, app_id="Probe")
    erste.acquire()

    fremd = SingleInstanceGuard(lock, app_id="Probe")
    fremd.release()

    assert lock.is_dir(), "die fremde Freigabe hat die Sperre entfernt"
    erste.release()


def test_als_kontextmanager(tmp_path):
    with SingleInstanceGuard(tmp_path / "lock", app_id="Probe") as guard:
        assert guard.acquire()[0]
    assert not (tmp_path / "lock").exists()


# ── PID-Pruefung ────────────────────────────────────────────────────────────

def test_der_eigene_prozess_lebt():
    assert is_pid_alive(os.getpid())


@pytest.mark.parametrize("wert", [None, 0, -1, "", "keine zahl"])
def test_unsinnige_pids_gelten_als_tot(wert):
    assert is_pid_alive(wert) is False
