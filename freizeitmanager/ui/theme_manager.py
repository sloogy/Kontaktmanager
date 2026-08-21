"""Theme-Verwaltung nach dem Vorbild des BudgetManagers.

Aufbau und Begruendung sind dort erprobt:

* Im Code stehen nur zwei Rueckfallprofile (hell und dunkel). Alles Weitere
  kommt als JSON aus ``ui/profiles`` und wird mitgeliefert.
* Aenderungen des Nutzers landen als eigene Datei im Datenordner und
  ueberschreiben das mitgelieferte Profil, ohne es zu zerstoeren.
* Ein fehlerhaftes Profil wird uebersprungen und protokolliert, statt die
  Anwendung farblos oder gar nicht starten zu lassen. Genau dafuer gibt es
  ``get_load_errors()``.

Angepasst an den FreizeitManager: Statt der Budget-Farben (Einnahmen,
Ausgaben, Ersparnisse) fuehrt ein Profil hier die Dringlichkeitsfarben der
Rotation. Alles Uebrige - Hintergruende, Text, Tabellen, Auswahl - bleibt
strukturgleich, damit sich die Module vertraut anfuehlen.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

MODE_LIGHT = "hell"
MODE_DARK = "dunkel"
MODES = (MODE_LIGHT, MODE_DARK)

# Gemeinsamer Bezugswert aller vier Programme: 10 heisst "normal".
REFERENCE_FONT_SIZE = 10
# Der FreizeitManager zeichnet bei "normal" 14 Punkt.
BASE_POINT_SIZE = 14
FONT_SIZE_MIN = 8
FONT_SIZE_MAX = 22

_HEX = re.compile(r"#[0-9a-fA-F]{6}")


def is_hex_color(value: Any) -> bool:
    return isinstance(value, str) and bool(_HEX.fullmatch(value.strip()))


def slugify(name: str) -> str:
    text = str(name or "").strip().lower()
    for source, target in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"),
                           ("–", "-"), ("—", "-")):
        text = text.replace(source, target)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_\-]", "", text).replace("-", "_")
    return re.sub(r"_+", "_", text).strip("_") or "profil"


# Vollstaendiger Schluesselsatz. Ein Profil darf Schluessel weglassen - dann
# gilt der Wert des passenden Rueckfallprofils. So bleiben aeltere oder von
# Hand geschriebene Profile gueltig, wenn spaeter Schluessel dazukommen.
COLOR_KEYS = (
    "hintergrund_app", "hintergrund_panel", "hintergrund_seitenleiste",
    "text", "text_gedimmt", "text_invers",
    # Eigener Schluessel: Die Seitenleiste ist in hellen Themes dunkel, ihr
    # Text also hell. "text_invers" meint dagegen Text auf der Akzentfarbe -
    # beides zu vermischen machte die Navigation in dunklen Themes unlesbar.
    "seitenleiste_text", "seitenleiste_text_gedimmt",
    "akzent", "akzent_text",
    "rand", "eingabe_hintergrund",
    "tabelle_hintergrund", "tabelle_alt", "tabelle_header", "tabelle_header_text",
    "tabelle_gitter", "auswahl_hintergrund", "auswahl_text",
    "hover_hintergrund", "hover_text",
    "karte_hintergrund", "karte_rand",
    "erfolg", "erfolg_text", "warnung", "gefahr",
    "ruhe_hintergrund", "ruhe_rand", "ruhe_text",
    # Dringlichkeitsfarben der Rotation - das Gegenstueck zu den
    # Budget-Typfarben im BudgetManager.
    "dringlichkeit_frisch", "dringlichkeit_bald",
    "dringlichkeit_faellig", "dringlichkeit_lange", "dringlichkeit_geplant",
)

BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "Standard - Hell": {
        "modus": MODE_LIGHT,
        "hintergrund_app": "#f1f5f9",
        "hintergrund_panel": "#ffffff",
        "hintergrund_seitenleiste": "#0b1220",
        "seitenleiste_text": "#f8fafc",
        "seitenleiste_text_gedimmt": "#94a3b8",
        "text": "#1e293b",
        "text_gedimmt": "#64748b",
        "text_invers": "#ffffff",
        "akzent": "#2563eb",
        "akzent_text": "#ffffff",
        "rand": "#cbd5e1",
        "eingabe_hintergrund": "#ffffff",
        "tabelle_hintergrund": "#ffffff",
        "tabelle_alt": "#f8fafc",
        "tabelle_header": "#f8fafc",
        "tabelle_header_text": "#475569",
        "tabelle_gitter": "#eef2f7",
        "auswahl_hintergrund": "#dbeafe",
        "auswahl_text": "#0f172a",
        "hover_hintergrund": "#e8f1ff",
        "hover_text": "#0f172a",
        "karte_hintergrund": "#ffffff",
        "karte_rand": "#dbe3ec",
        "erfolg": "#16a34a",
        "erfolg_text": "#ffffff",
        "warnung": "#ca8a04",
        "gefahr": "#dc2626",
        "ruhe_hintergrund": "#f0fdf4",
        "ruhe_rand": "#86efac",
        "ruhe_text": "#15803d",
        "dringlichkeit_frisch": "#16a34a",
        "dringlichkeit_bald": "#ca8a04",
        "dringlichkeit_faellig": "#ea580c",
        "dringlichkeit_lange": "#2563eb",
        "dringlichkeit_geplant": "#0891b2",
        "schriftgroesse": 10,
    },
    "Standard - Dunkel": {
        "modus": MODE_DARK,
        "hintergrund_app": "#0f172a",
        "hintergrund_panel": "#1e293b",
        "hintergrund_seitenleiste": "#020617",
        "seitenleiste_text": "#e2e8f0",
        "seitenleiste_text_gedimmt": "#94a3b8",
        "text": "#e2e8f0",
        "text_gedimmt": "#94a3b8",
        "text_invers": "#0f172a",
        "akzent": "#3b82f6",
        "akzent_text": "#ffffff",
        "rand": "#334155",
        "eingabe_hintergrund": "#1e293b",
        "tabelle_hintergrund": "#1e293b",
        "tabelle_alt": "#243044",
        "tabelle_header": "#0f172a",
        "tabelle_header_text": "#94a3b8",
        "tabelle_gitter": "#334155",
        "auswahl_hintergrund": "#1d4ed8",
        "auswahl_text": "#ffffff",
        "hover_hintergrund": "#1e3a8a",
        "hover_text": "#e2e8f0",
        "karte_hintergrund": "#1e293b",
        "karte_rand": "#334155",
        "erfolg": "#22c55e",
        "erfolg_text": "#052e16",
        "warnung": "#eab308",
        "gefahr": "#ef4444",
        "ruhe_hintergrund": "#052e16",
        "ruhe_rand": "#166534",
        "ruhe_text": "#86efac",
        "dringlichkeit_frisch": "#4ade80",
        "dringlichkeit_bald": "#facc15",
        "dringlichkeit_faellig": "#fb923c",
        "dringlichkeit_lange": "#60a5fa",
        "dringlichkeit_geplant": "#22d3ee",
        "schriftgroesse": 10,
    },
}

DEFAULT_PROFILE = "Standard - Hell"

# Umbenannte Profile: alte Einstellung weiterhin aufloesen.
ALIASES: dict[str, str] = {
    # Dieselben Designs trugen in den Programmen verschiedene Namen - wer im
    # LifePlanner "Kontrast - Schwarz/Weiss" waehlte, fand hier nur
    # "Kontrast Schwarzweiss" und bekam deshalb ein halb uebernommenes Design.
    # Ab jetzt gilt der Name des Hosts; gespeicherte Einstellungen loesen
    # weiterhin auf.
    "Standard Hell": "Standard - Hell",
    "Standard Dunkel": "Standard - Dunkel",
    "Kontrast Schwarzweiss": "Kontrast - Schwarz/Weiß",
    "Warm Sepia - Hell": "Hell - Warm (Sepia)",
    "OLED Schwarz": "Dunkel - OLED (Kontrastarm)",
}


@dataclass
class ThemeProfile:
    name: str
    data: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    @property
    def mode(self) -> str:
        return str(self.data.get("modus", MODE_LIGHT)).strip().lower()

    @property
    def is_dark(self) -> bool:
        return self.mode == MODE_DARK

    @property
    def font_size(self) -> int:
        """Schriftgroesse auf dem gemeinsamen Massstab; 10 heisst unveraendert.

        Der Wert steht so auch in den Profilen der Schwesterprogramme. Frueher
        fuehrte der FreizeitManager hier 14 - dasselbe Design ergab dann in
        jedem Programm eine andere Schriftgroesse.
        """
        try:
            size = int(self.data.get("schriftgroesse", REFERENCE_FONT_SIZE))
        except (TypeError, ValueError):
            size = REFERENCE_FONT_SIZE
        return max(FONT_SIZE_MIN, min(FONT_SIZE_MAX, size))

    @property
    def point_size(self) -> int:
        """Die tatsaechliche Schriftgroesse des FreizeitManagers.

        Er zeichnet seit jeher eine Stufe groesser als die Schwesterprogramme.
        Das bleibt so - der gemeinsame Wert wirkt als Faktor darauf.
        """
        scaled = BASE_POINT_SIZE * self.font_size / float(REFERENCE_FONT_SIZE)
        return max(FONT_SIZE_MIN, min(FONT_SIZE_MAX, int(round(scaled))))

    def color(self, key: str) -> str:
        """Farbe mit Rueckfall auf das Standardprofil der gleichen Helligkeit."""
        value = self.data.get(key)
        if is_hex_color(value):
            return str(value).strip()
        fallback = BUILTIN_PROFILES["Standard - Dunkel" if self.is_dark else "Standard - Hell"]
        return str(fallback.get(key, "#808080"))

    def to_dict(self) -> dict[str, Any]:
        return dict(self.data)


def validate_profile_data(data: dict[str, Any]) -> tuple[bool, str]:
    """Prueft ein Profil, bevor es angeboten wird."""
    mode = str(data.get("modus", MODE_LIGHT)).strip().lower()
    if mode not in MODES:
        return False, f"Ungueltiger modus: {mode!r} (erlaubt: {', '.join(MODES)})"

    raw_size = data.get("schriftgroesse", REFERENCE_FONT_SIZE)
    try:
        size = int(raw_size)
    except (TypeError, ValueError):
        return False, f"Ungueltige schriftgroesse: {raw_size!r}"
    if not FONT_SIZE_MIN <= size <= FONT_SIZE_MAX:
        return False, f"schriftgroesse ausserhalb {FONT_SIZE_MIN}-{FONT_SIZE_MAX}: {size}"

    for key, value in data.items():
        if key in ("modus", "schriftgroesse") or key.startswith("_"):
            continue
        if isinstance(value, str) and value.strip().startswith("#") and not is_hex_color(value):
            return False, f"Ungueltige Farbe {key}={value!r}"
    return True, ""


class ThemeManager:
    """Singleton. Kennt alle Profile, das aktive und baut das Stylesheet."""

    _instance: ThemeManager | None = None

    def __init__(self) -> None:
        self._bundled: dict[str, Path] = {}
        self._user: dict[str, Path] = {}
        self._errors: list[tuple[str, str, str]] = []
        self._current: ThemeProfile | None = None
        self.rescan()

    @classmethod
    def instance(cls) -> ThemeManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Nur fuer Tests und Profilwechsel."""
        cls._instance = None

    # ── Ablageorte ───────────────────────────────────────────────────────────
    @staticmethod
    def bundled_dir() -> Path:
        """Mitgelieferte Profile - im Quellbaum wie im gebauten Paket."""
        import sys
        bundle = getattr(sys, "_MEIPASS", "")
        if bundle:
            packed = Path(bundle) / "freizeitmanager" / "ui" / "profiles"
            if packed.is_dir():
                return packed
        return Path(__file__).resolve().parent / "profiles"

    @staticmethod
    def user_dir() -> Path:
        from freizeitmanager import paths
        target = paths.data_dir() / "theme_profiles"
        target.mkdir(parents=True, exist_ok=True)
        return target

    # ── Einlesen ─────────────────────────────────────────────────────────────
    def rescan(self) -> None:
        self._bundled, self._user, self._errors = {}, {}, []
        self._scan(self.bundled_dir(), self._bundled)
        try:
            self._scan(self.user_dir(), self._user)
        except OSError as exc:
            _log.warning("Eigene Themes nicht lesbar: %s", exc)

    def _scan(self, directory: Path, target: dict[str, Path]) -> None:
        if not directory.is_dir():
            return
        for file in sorted(directory.glob("*.json")):
            name = file.stem.replace("_", " ").strip()
            try:
                raw = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self._record_error(name, file, f"JSON-Ladefehler: {exc}")
                continue
            if not isinstance(raw, dict):
                self._record_error(name, file, "Profil ist kein JSON-Objekt")
                continue
            name = str(raw.get("name") or "").strip() or name
            data = {k: v for k, v in raw.items() if k != "name"}
            ok, message = validate_profile_data(data)
            if not ok:
                self._record_error(name, file, message)
                continue
            target[name] = file

    def _record_error(self, name: str, path: Path, message: str) -> None:
        """Fehlerhafte Profile werden uebersprungen, nicht verschwiegen."""
        self._errors.append((name, str(path), message))
        _log.warning("Theme-Profil uebersprungen: %s (%s): %s", name, path, message)
        try:
            from freizeitmanager import paths
            log_path = paths.logs_dir() / "theme_profile_errors.log"
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"[{name}] {path}: {message}\n")
        except OSError:
            pass

    def get_load_errors(self) -> list[tuple[str, str, str]]:
        return list(self._errors)

    # ── Profile ──────────────────────────────────────────────────────────────
    def available_profiles(self) -> list[str]:
        names = set(self._bundled) | set(self._user) | set(BUILTIN_PROFILES)
        names -= set(ALIASES)
        return sorted(names, key=str.casefold)

    def _resolve(self, name: str) -> str:
        return ALIASES.get(str(name or "").strip(), str(name or "").strip())

    def is_bundled(self, name: str) -> bool:
        return self._resolve(name) in self._bundled

    def has_override(self, name: str) -> bool:
        return self._resolve(name) in self._user

    def get_profile(self, name: str) -> ThemeProfile | None:
        """Reihenfolge: eigene Fassung, dann mitgeliefert, dann eingebaut."""
        name = self._resolve(name)
        for index in (self._user, self._bundled):
            path = index.get(name)
            if path is None:
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self._record_error(name, path, f"JSON-Ladefehler: {exc}")
                continue
            return ThemeProfile(name, {k: v for k, v in raw.items() if k != "name"})
        if name in BUILTIN_PROFILES:
            return ThemeProfile(name, dict(BUILTIN_PROFILES[name]))
        return None

    def current_name(self) -> str:
        from freizeitmanager.database import db
        with db.get_session() as session:
            return self._resolve(db.get_setting(session, "ui.theme", DEFAULT_PROFILE))

    def follows_shared(self) -> bool:
        """Uebernimmt dieses Modul das gemeinsame Theme des LifePlanners?"""
        from freizeitmanager.database import db
        with db.get_session() as session:
            return db.get_bool_setting(session, "ui.theme_follow_shared", True)

    def set_follows_shared(self, value: bool) -> None:
        from freizeitmanager.database import db
        with db.get_session() as session:
            db.set_setting(session, "ui.theme_follow_shared", "1" if value else "0")
        self._current = None

    def shared_profile(self) -> ThemeProfile | None:
        """Das gemeinsame Theme als Profil - oder None."""
        from freizeitmanager.integration.shared_theme import read_shared_theme, shared_theme_as_profile_data
        data = read_shared_theme()
        if data is None:
            return None
        name = str(data.get("name", "")).strip()
        # Kennt das Modul das Profil selbst, hat die eigene Fassung Vorrang:
        # sie ist vollstaendig, die uebergebenen Farben sind nur ein Auszug.
        local = self.get_profile(name)
        if local is not None:
            return local
        payload = shared_theme_as_profile_data(data)
        ok, message = validate_profile_data(payload)
        if not ok:
            _log.warning("Gemeinsames Theme %r ist ungueltig: %s", name, message)
            return None
        return ThemeProfile(name, payload)

    def current_profile(self) -> ThemeProfile:
        """Immer ein gueltiges Profil - notfalls das eingebaute helle.

        Reihenfolge: gemeinsames Theme (wenn eingeschaltet und vorhanden),
        sonst die lokale Wahl, sonst das eingebaute helle Profil.
        """
        if self._current is not None:
            return self._current
        profile = None
        if self.follows_shared():
            profile = self.shared_profile()
        if profile is None:
            profile = self.get_profile(self.current_name())
        if profile is None:
            _log.warning("Theme %r nicht gefunden, nutze %s", self.current_name(), DEFAULT_PROFILE)
            profile = ThemeProfile(DEFAULT_PROFILE, dict(BUILTIN_PROFILES[DEFAULT_PROFILE]))
        self._current = profile
        return profile

    def apply_to_all_modules(self, name: str) -> Path | None:
        """Setzt dieses Theme fuer alle Module des Profils.

        Ausdrueckliche Handlung des Nutzers - siehe integration/shared_theme.py.
        """
        from freizeitmanager.integration.shared_theme import publish_shared_theme
        profile = self.get_profile(name)
        if profile is None:
            raise ValueError(f"Unbekanntes Theme: {name!r}")
        return publish_shared_theme(profile.name, profile.to_dict())

    def set_current(self, name: str, *, for_all_modules: bool = False) -> ThemeProfile:
        """Waehlt das Theme. ``for_all_modules`` veroeffentlicht es zusaetzlich."""
        from freizeitmanager.database import db
        profile = self.get_profile(name)
        if profile is None:
            raise ValueError(f"Unbekanntes Theme: {name!r}")
        with db.get_session() as session:
            db.set_setting(session, "ui.theme", profile.name)
        self._current = profile
        if for_all_modules:
            self.apply_to_all_modules(profile.name)
        return profile

    # ── Eigene Fassungen ─────────────────────────────────────────────────────
    def save_override(self, name: str, data: dict[str, Any]) -> Path:
        """Speichert eine eigene Fassung. Das Mitgelieferte bleibt unberuehrt."""
        name = self._resolve(name)
        ok, message = validate_profile_data(data)
        if not ok:
            raise ValueError(message)
        payload = {"name": name, **data}
        path = self.user_dir() / f"{slugify(name)}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        self.rescan()
        if self._current is not None and self._current.name == name:
            self._current = self.get_profile(name)
        return path

    def reset_override(self, name: str) -> bool:
        """Eigene Fassung verwerfen und zum mitgelieferten Stand zurueck."""
        name = self._resolve(name)
        path = self._user.get(name)
        if path is None:
            return False
        path.unlink(missing_ok=True)
        self.rescan()
        if self._current is not None and self._current.name == name:
            self._current = self.get_profile(name)
        return True
