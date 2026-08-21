"""Themeverwaltung: Profile, eigene Fassungen und das gemeinsame Theme."""
from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from freizeitmanager.ui.theme_manager import (
    BUILTIN_PROFILES,
    COLOR_KEYS,
    DEFAULT_PROFILE,
    MODES,
    ThemeManager,
    ThemeProfile,
    slugify,
    validate_profile_data,
)


@pytest.fixture()
def manager(session):
    ThemeManager.reset()
    yield ThemeManager.instance()
    ThemeManager.reset()


# ── Profile ─────────────────────────────────────────────────────────────────

def test_mitgelieferte_profile_sind_alle_gueltig(manager):
    """Ein kaputtes Profil wuerde stillschweigend fehlen."""
    assert manager.get_load_errors() == []
    names = manager.available_profiles()
    assert len(names) >= 8
    assert set(BUILTIN_PROFILES) <= set(names)


def test_jedes_profil_deckt_alle_farbschluessel_ab(manager):
    """Fehlende Schluessel duerfen nicht in grauen Flaechen enden."""
    for name in manager.available_profiles():
        profile = manager.get_profile(name)
        assert profile is not None, name
        assert profile.mode in MODES, name
        for key in COLOR_KEYS:
            value = profile.color(key)
            assert value.startswith("#") and len(value) == 7, f"{name}/{key}={value}"


def test_ungueltige_profile_werden_abgewiesen():
    assert validate_profile_data({"modus": "bunt"})[0] is False
    assert validate_profile_data({"modus": "hell", "schriftgroesse": 99})[0] is False
    assert validate_profile_data({"modus": "hell", "text": "#xyz"})[0] is False
    assert validate_profile_data({"modus": "hell", "schriftgroesse": 14})[0] is True


def test_kaputte_datei_wird_uebersprungen_nicht_verschluckt(manager, tmp_path, monkeypatch):
    monkeypatch.setattr(ThemeManager, "user_dir", staticmethod(lambda: tmp_path))
    (tmp_path / "kaputt.json").write_text("{kein json", encoding="utf-8")
    (tmp_path / "falsch.json").write_text(
        json.dumps({"name": "Falsch", "modus": "bunt"}), encoding="utf-8")
    manager.rescan()

    errors = {name for name, _path, _msg in manager.get_load_errors()}
    assert errors == {"kaputt", "Falsch"}
    assert "Falsch" not in manager.available_profiles()
    # Die Anwendung bleibt trotzdem bedienbar.
    assert manager.current_profile().name


def test_unbekanntes_theme_faellt_auf_den_standard_zurueck(manager, session):
    from freizeitmanager.database import db
    db.set_setting(session, "ui.theme", "Gibt Es Nicht")
    session.commit()
    ThemeManager.reset()
    assert ThemeManager.instance().current_profile().name == DEFAULT_PROFILE


def test_slugify_haelt_dateinamen_sauber():
    assert slugify("Nord - Dunkel") == "nord_dunkel"
    assert slugify("Warm Sepia – Hell") == "warm_sepia_hell"
    assert slugify("Grün & Grau!") == "gruen_grau"


# ── Eigene Fassungen ────────────────────────────────────────────────────────

def test_eigene_fassung_ueberschreibt_das_mitgelieferte_profil(manager, tmp_path, monkeypatch):
    monkeypatch.setattr(ThemeManager, "user_dir", staticmethod(lambda: tmp_path))
    manager.rescan()
    original = manager.get_profile("Nord - Dunkel")
    data = original.to_dict()
    data["schriftgroesse"] = 18

    manager.save_override("Nord - Dunkel", data)
    assert manager.has_override("Nord - Dunkel")
    assert manager.get_profile("Nord - Dunkel").font_size == 18

    manager.reset_override("Nord - Dunkel")
    assert not manager.has_override("Nord - Dunkel")
    # Das mitgelieferte Profil hat die Aenderung nie gesehen.
    assert manager.get_profile("Nord - Dunkel").font_size == original.font_size


def test_ungueltige_eigene_fassung_wird_nicht_gespeichert(manager, tmp_path, monkeypatch):
    monkeypatch.setattr(ThemeManager, "user_dir", staticmethod(lambda: tmp_path))
    with pytest.raises(ValueError):
        manager.save_override("Kaputt", {"modus": "hell", "text": "#zzz"})
    assert not list(tmp_path.glob("*.json"))


# ── Stylesheet ──────────────────────────────────────────────────────────────

def test_stylesheet_folgt_dem_profil(manager):
    from freizeitmanager.ui.styles import get_stylesheet
    hell = get_stylesheet(1.0, manager.get_profile("Standard Hell"))
    dunkel = get_stylesheet(1.0, manager.get_profile("OLED Schwarz"))
    assert hell != dunkel
    assert "#000000" in dunkel
    assert manager.get_profile("Standard Hell").color("hintergrund_app") in hell


def test_schriftgroesse_wirkt_im_stylesheet(manager):
    from freizeitmanager.ui.styles import get_stylesheet
    css = get_stylesheet(1.0, ThemeProfile("T", {"modus": "hell", "schriftgroesse": 20}))
    assert "font-size: 20px" in css


# ── Gemeinsames Theme ueber die Bridge ──────────────────────────────────────

def test_ohne_host_passiert_nichts(manager, monkeypatch):
    from freizeitmanager.integration import shared_theme as st
    monkeypatch.delenv("LIFEPLANNER_BRIDGE_DIR", raising=False)
    assert st.shared_theme_path() is None
    assert st.read_shared_theme() is None
    assert st.publish_shared_theme("Nord - Dunkel", BUILTIN_PROFILES["Standard - Dunkel"]) is None


def test_veroeffentlichtes_theme_haelt_das_schema(manager, tmp_path, monkeypatch):
    from freizeitmanager.integration import shared_theme as st
    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path))
    manager.apply_to_all_modules("Nord - Dunkel")

    record = json.loads((tmp_path / st.SHARED_THEME_FILE).read_text(encoding="utf-8"))
    assert record["schema"] == st.SHARED_THEME_SCHEMA
    assert record["name"] == "Nord - Dunkel"
    assert record["modus"] == "dunkel"
    assert record["gesetzt_von"] == "freizeitmanager"
    assert len(record["farben"]) >= 20
    assert not list(tmp_path.glob("*.tmp")), "atomar schreiben, keine Reste"


def test_zweites_modul_uebernimmt_das_gemeinsame_theme(manager, tmp_path, monkeypatch):
    """Der eigentliche Zweck: alle Module sehen gleich aus."""
    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path))
    manager.apply_to_all_modules("Dracula - Dunkel")

    ThemeManager.reset()
    other = ThemeManager.instance()
    assert other.follows_shared()
    assert other.current_profile().name == "Dracula - Dunkel"
    assert other.current_profile().is_dark


def test_folgen_laesst_sich_abschalten(manager, tmp_path, monkeypatch):
    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path))
    manager.apply_to_all_modules("Dracula - Dunkel")
    ThemeManager.reset()

    other = ThemeManager.instance()
    other.set_follows_shared(False)
    assert other.current_profile().name == DEFAULT_PROFILE


def test_beschaedigtes_gemeinsames_theme_wird_ignoriert(manager, tmp_path, monkeypatch):
    """Eine kaputte Bridge-Datei darf kein Modul unbedienbar machen."""
    from freizeitmanager.integration import shared_theme as st
    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path))
    (tmp_path / st.SHARED_THEME_FILE).write_text("{kaputt", encoding="utf-8")
    ThemeManager.reset()
    assert ThemeManager.instance().current_profile().name == DEFAULT_PROFILE

    (tmp_path / st.SHARED_THEME_FILE).write_text(
        json.dumps({"schema": "fremd.v9", "name": "X"}), encoding="utf-8")
    ThemeManager.reset()
    assert ThemeManager.instance().current_profile().name == DEFAULT_PROFILE


def test_lokal_bekanntes_profil_hat_vorrang_vor_den_uebergebenen_farben(manager, tmp_path, monkeypatch):
    """Die Bridge traegt nur einen Farbauszug - die eigene Fassung ist vollstaendig."""
    from freizeitmanager.integration import shared_theme as st
    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path))
    (tmp_path / st.SHARED_THEME_FILE).write_text(json.dumps({
        "schema": st.SHARED_THEME_SCHEMA,
        "name": "Nord - Dunkel",
        "modus": "dunkel",
        "schriftgroesse": 14,
        "farben": {"akzent": "#ff0000"},
        "gesetzt_von": "budgetmanager",
    }), encoding="utf-8")
    ThemeManager.reset()
    profile = ThemeManager.instance().current_profile()
    assert profile.name == "Nord - Dunkel"
    assert profile.color("akzent") == "#88c0d0"


def test_fremdes_modul_kann_ein_unbekanntes_theme_setzen(manager, tmp_path, monkeypatch):
    """Ein Theme, das nur der BudgetManager mitliefert, muss trotzdem wirken."""
    from freizeitmanager.integration import shared_theme as st
    monkeypatch.setenv("LIFEPLANNER_BRIDGE_DIR", str(tmp_path))
    farben = {key: "#123456" for key in COLOR_KEYS}
    (tmp_path / st.SHARED_THEME_FILE).write_text(json.dumps({
        "schema": st.SHARED_THEME_SCHEMA,
        "name": "Fremdes Design",
        "modus": "hell",
        "schriftgroesse": 15,
        "farben": farben,
        "gesetzt_von": "budgetmanager",
    }), encoding="utf-8")
    ThemeManager.reset()
    profile = ThemeManager.instance().current_profile()
    assert profile.name == "Fremdes Design"
    assert profile.color("akzent") == "#123456"
    assert profile.font_size == 15


# ── Lesbarkeit ──────────────────────────────────────────────────────────────

def _luminance(hex_color: str) -> float:
    """Relative Helligkeit nach WCAG."""
    parts = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in parts]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


# (Vordergrund, Hintergrund) - Paare, die in der Oberflaeche wirklich
# aufeinandertreffen. Alle drei hier gelisteten Faelle waren echte Fehler:
# Seitenleistentext, Modusknopf und Kacheltext waren jeweils unlesbar.
CONTRAST_PAIRS = (
    ("text", "hintergrund_app"),
    ("text", "hintergrund_panel"),
    ("text", "karte_hintergrund"),
    ("text_gedimmt", "karte_hintergrund"),
    ("seitenleiste_text", "hintergrund_seitenleiste"),
    ("seitenleiste_text_gedimmt", "hintergrund_seitenleiste"),
    ("akzent_text", "akzent"),
    ("erfolg_text", "erfolg"),
    ("auswahl_text", "auswahl_hintergrund"),
    ("tabelle_header_text", "tabelle_header"),
    ("text", "tabelle_hintergrund"),
    ("text", "tabelle_alt"),
    ("hover_text", "hover_hintergrund"),
    ("ruhe_text", "ruhe_hintergrund"),
)

# 3.0 statt der strengen 4.5: Es geht hier nicht um eine
# Barrierefreiheitszertifizierung, sondern darum, echte Unlesbarkeit
# (gleiche oder fast gleiche Farbe) sicher zu erwischen.
MIN_CONTRAST = 3.0


def test_jedes_profil_ist_lesbar(manager):
    problems: list[str] = []
    for name in manager.available_profiles():
        profile = manager.get_profile(name)
        for foreground, background in CONTRAST_PAIRS:
            ratio = contrast_ratio(profile.color(foreground), profile.color(background))
            if ratio < MIN_CONTRAST:
                problems.append(f"{name}: {foreground} auf {background} = {ratio:.2f}")
    assert not problems, "Zu geringer Kontrast:\n  " + "\n  ".join(problems)


def test_dringlichkeitsfarben_heben_sich_ab(manager):
    """Die Ampel ist der wichtigste Signaltraeger - sie muss sichtbar sein."""
    problems: list[str] = []
    for name in manager.available_profiles():
        profile = manager.get_profile(name)
        for key in ("dringlichkeit_frisch", "dringlichkeit_bald",
                    "dringlichkeit_faellig", "dringlichkeit_lange",
                    "dringlichkeit_geplant"):
            ratio = contrast_ratio(profile.color(key), profile.color("karte_hintergrund"))
            if ratio < 2.0:
                problems.append(f"{name}: {key} = {ratio:.2f}")
    assert not problems, "Ampelfarbe zu schwach:\n  " + "\n  ".join(problems)
