"""Leitet saemtliche Markenbilder des FreizeitManagers aus zwei Quellbildern ab.

Quellen:
    freizeitmanager/resources/icons/freizeitmanager-source.png       (Motiv)
    freizeitmanager/resources/icons/freizeitmanager-logo-source.png  (Banner)

Ziele:
    freizeitmanager/resources/icons/freizeitmanager-{16,...,512}.png
    freizeitmanager/resources/icons/freizeitmanager.png       (1024 px, Qt/Linux)
    freizeitmanager/resources/icons/freizeitmanager.ico       (Windows)
    freizeitmanager/resources/icons/freizeitmanager-logo.png       (helle Flaechen)
    freizeitmanager/resources/icons/freizeitmanager-logo-hell.png  (dunkle Flaechen)

Warum die Quellbilder nicht direkt ausgeliefert werden
------------------------------------------------------
Die Bildmappe der Suite liefert PNGs mit ungleichen unsichtbaren Raendern -
beim Banner 25 Bildpunkte links und 88 rechts, 27 oben und 52 unten. Wer ein
solches Bild in eine Flaeche fester Hoehe legt, bekommt ein Logo, das zu klein
wirkt und sichtbar aus der Mitte rutscht, obwohl das Layout korrekt zentriert.
Deshalb:

* ``trimmed`` schneidet die unsichtbaren Raender weg. Danach ist die Bildkante
  die Motivkante, und eine Skalierung auf Breite fuellt die Flaeche wirklich.
* ``square`` setzt das Icon-Motiv mittig auf ein transparentes Quadrat mit
  gleichem Rand ringsum. Randlos darf ein Icon nicht sein - in 16 px klebt es
  sonst an der Kante -, aber der Rand muss auf allen vier Seiten gleich sein,
  sonst haengt das Symbol neben anderen Symbolen sichtbar schief.

Warum es das Banner zweimal gibt
--------------------------------
Der Schriftzug ist zur Haelfte dunkelblau (#0D1B3A). Auf hellem Grund ist das
richtig; die Seitenleisten der dunklen Profile gehen bis #050505, dort waere
das halbe Wort weg. Welche Fassung erscheint, entscheidet zur Laufzeit
``freizeitmanager.ui.branding`` anhand des aktiven Profils.

Benoetigt: pip install Pillow

Ausfuehren (aus dem Projektroot):
    python tools/create_icons.py
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Fehler: Pillow ist nicht installiert.")
    print("Installiere mit: pip install Pillow")
    sys.exit(1)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = PROJECT_ROOT / "freizeitmanager" / "resources" / "icons"
STAMM = "freizeitmanager"

SOURCE_PATH = ICON_DIR / f"{STAMM}-source.png"
LOGO_SOURCE_PATH = ICON_DIR / f"{STAMM}-logo-source.png"
LOGO_PATH = ICON_DIR / f"{STAMM}-logo.png"
LOGO_HELL_PATH = ICON_DIR / f"{STAMM}-logo-hell.png"

#: Einzel-PNGs fuer Qt und die Linux-Desktops.
PNG_SIZES = (16, 32, 48, 64, 128, 256, 512)

#: Groesse der generischen freizeitmanager.png.
MAIN_PNG_SIZE = 1024

#: Mehrfachaufloesung in der .ico. Windows waehlt je nach Kontext eine davon.
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

#: Rand je Seite des quadratischen Icons, als Anteil der Kantenlaenge.
ICON_MARGIN_RATIO = 0.02

# Ab welchem Alphawert ein Bildpunkt als Motiv zaehlt.
#
# Die gelieferten PNGs tragen ueber das ganze Blatt einen Schleier mit Alpha 1
# bis 3 - unsichtbar, aber fuer getbbox deckend. Ein Zuschnitt auf "Alpha > 0"
# schnitte deshalb gar nichts weg. Zwischen 8 und 128 verschiebt sich der
# Rahmen um hoechstens einen Bildpunkt, die Schwelle ist also unkritisch.
ALPHA_SCHWELLE = 8

# Die vier Flaechenfarben der Bildmappe und ihre Entsprechung fuer dunkle
# Flaechen. Zugeordnet wird ueber den naechstliegenden Ankerpunkt: Die Bilder
# bestehen aus flachen Farbfeldern, die nur gegen die Transparenz
# weichgezeichnet sind - zwischen zwei Feldern liegen kaum Mischwerte, an
# denen die Zuordnung kippen koennte.
FARB_ANKER: tuple[tuple[tuple[int, int, int], tuple[int, int, int]], ...] = (
    ((13, 27, 58), (255, 255, 255)),      # Dunkelblau -> Weiss
    ((14, 116, 144), (77, 195, 220)),     # Petrol -> helles Petrol
    ((86, 180, 74), (124, 214, 112)),     # Gruen -> helles Gruen
    ((245, 245, 245), (245, 245, 245)),   # Weiss bleibt Weiss
)


def _load(path: Path, beschreibung: str) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(
            f"Quellbild fehlt: {path}\nOhne {beschreibung} laesst sich nichts erzeugen."
        )
    return Image.open(path).convert("RGBA")


def motiv_rahmen(image: Image.Image, *, schwelle: int = ALPHA_SCHWELLE):
    """Rahmen um alles, was sichtbar zum Motiv gehoert - oder ``None``."""
    maske = image.getchannel("A").point(lambda wert: 255 if wert > schwelle else 0)
    return maske.getbbox()


def trimmed(image: Image.Image) -> Image.Image:
    """Schneidet die unsichtbaren Raender weg."""
    box = motiv_rahmen(image)
    if box is None or box == (0, 0, image.width, image.height):
        return image
    return image.crop(box)


def square(image: Image.Image, *, margin_ratio: float = ICON_MARGIN_RATIO) -> Image.Image:
    """Setzt ``image`` mittig auf ein transparentes Quadrat mit gleichem Rand."""
    longest = max(image.width, image.height)
    # Der Rand kommt beidseitig dazu, deshalb geht er zweimal in die Kante ein.
    edge = int(round(longest / max(1e-6, 1.0 - 2.0 * margin_ratio)))
    canvas = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
    canvas.paste(image, ((edge - image.width) // 2, (edge - image.height) // 2), image)
    return canvas


def fuer_dunkle_flaechen(image: Image.Image) -> Image.Image:
    """Faerbt das Bild fuer dunklen Untergrund um.

    Jeder sichtbare Bildpunkt bekommt die Zielfarbe des naechstliegenden
    Ankers aus :data:`FARB_ANKER`. Unsichtbare Bildpunkte bleiben unberuehrt:
    Ihre Farbe wird nie gezeigt, und der Schleier aus der Bildmappe traegt
    Werte, die jede Zuordnung nur verwirren wuerden.
    """
    anker = list(FARB_ANKER)
    zwischenspeicher: dict[tuple[int, int, int], tuple[int, int, int]] = {}

    def ziel(farbe: tuple[int, int, int]) -> tuple[int, int, int]:
        treffer = zwischenspeicher.get(farbe)
        if treffer is None:
            r, g, b = farbe
            treffer = min(
                anker,
                key=lambda paar: (paar[0][0] - r) ** 2
                + (paar[0][1] - g) ** 2
                + (paar[0][2] - b) ** 2,
            )[1]
            zwischenspeicher[farbe] = treffer
        return treffer

    # Ueber die Rohbytes statt ueber getdata/putdata: das spart eine Million
    # Tupelobjekte und laeuft auf jeder Pillow-Fassung ohne Verfallshinweis.
    roh = bytearray(image.tobytes())
    for i in range(0, len(roh), 4):
        if roh[i + 3] <= ALPHA_SCHWELLE:
            continue
        roh[i], roh[i + 1], roh[i + 2] = ziel((roh[i], roh[i + 1], roh[i + 2]))
    return Image.frombytes("RGBA", image.size, bytes(roh))


def scaled(source: Image.Image, size: int) -> Image.Image:
    return source.resize((size, size), Image.LANCZOS)


def write_pngs(source: Image.Image) -> list[Path]:
    written: list[Path] = []
    for size in PNG_SIZES:
        target = ICON_DIR / f"{STAMM}-{size}.png"
        scaled(source, size).save(target, format="PNG")
        written.append(target)
    main_png = ICON_DIR / f"{STAMM}.png"
    scaled(source, MAIN_PNG_SIZE).save(main_png, format="PNG")
    written.append(main_png)
    return written


def write_ico(source: Image.Image) -> Path:
    target = ICON_DIR / f"{STAMM}.ico"
    scaled(source, max(ICO_SIZES)).save(
        target, format="ICO", sizes=[(s, s) for s in ICO_SIZES]
    )
    return target


def write_logo(source: Image.Image) -> list[Path]:
    source.save(LOGO_PATH, format="PNG")
    fuer_dunkle_flaechen(source).save(LOGO_HELL_PATH, format="PNG")
    return [LOGO_PATH, LOGO_HELL_PATH]


def create_icons() -> int:
    ICON_DIR.mkdir(parents=True, exist_ok=True)

    motiv = square(trimmed(_load(SOURCE_PATH, "das Markenbild")))
    print(f"Icon-Quelle : {SOURCE_PATH.name} -> {motiv.width}x{motiv.height}")
    for path in write_pngs(motiv):
        print(f"  geschrieben: {path.relative_to(PROJECT_ROOT)}")
    ico = write_ico(motiv)
    print(
        f"  geschrieben: {ico.relative_to(PROJECT_ROOT)} "
        f"({', '.join(str(s) for s in ICO_SIZES)} px)"
    )

    banner = trimmed(_load(LOGO_SOURCE_PATH, "das Logo-Banner"))
    print(f"Logo-Quelle : {LOGO_SOURCE_PATH.name} -> {banner.width}x{banner.height}")
    for path in write_logo(banner):
        print(f"  geschrieben: {path.relative_to(PROJECT_ROOT)}")
    print("Fertig.")
    return 0


def main() -> int:
    try:
        return create_icons()
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Fehler: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
