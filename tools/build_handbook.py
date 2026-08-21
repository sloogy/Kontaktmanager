#!/usr/bin/env python3
"""Baut Handbuch und Hilfeseite aus den Texten der In-App-Hilfe.

Bewusst eine einzige Quelle: Die Hilfethemen stehen in ``i18n/<sprache>.json``
unter ``help.topics`` und werden dort gepflegt. Ein zweiter, von Hand
gefuehrter Handbuchtext wuerde binnen zweier Releases davon abweichen - im
BudgetManager war genau das der Grund, die Hilfe generieren zu lassen.

In allen drei Sprachen, weil die Oberflaeche es auch ist. Erzeugt wurde lange
nur die deutsche Fassung, obwohl die Hilfetexte selbst schon uebersetzt
vorlagen - wer das Programm auf Englisch oder Franzoesisch benutzte, fand
daneben ein deutsches Handbuch.

    python tools/build_handbook.py [--check]

``--check`` schreibt nichts und meldet mit Exitcode 1, wenn die erzeugten
Dateien nicht mehr zum Stand der Sprachdateien passen.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SPRACHEN = ("de", "en", "fr")


def guide_pfad(sprache: str) -> Path:
    return ROOT / "docs" / f"USER_GUIDE.{sprache}.md"


def page_pfad(sprache: str) -> Path:
    # Deutsch behaelt index.html, damit bestehende Verweise nicht brechen.
    name = "index.html" if sprache == "de" else f"index.{sprache}.html"
    return ROOT / "docs" / "help" / name


# Rueckwaertskompatible Namen; einige Tests und Skripte greifen darauf zu.
GUIDE = guide_pfad("de")
PAGE = page_pfad("de")

INTRO = {
    "de": """Der FreizeitManager hilft dabei, Beziehungen zu pflegen, ohne daraus eine
Pflichtenliste zu machen. Er merkt sich, wer wie wichtig ist und in welchem
Rhythmus Kontakt gewuenscht ist, und schlaegt taeglich hoechstens eine Handvoll
Menschen vor.

Dieses Handbuch wird aus der Hilfe in der Anwendung erzeugt. Dieselben Texte
erreichen Sie dort jederzeit mit **F1**.""",
    "en": """FreizeitManager helps you keep up with the people who matter, without
turning that into a list of chores. It remembers who is important to you and
how often you would like to be in touch, and suggests at most a handful of
people each day.

This manual is generated from the help inside the application. The same texts
are always available there with **F1**.""",
    "fr": """FreizeitManager vous aide à entretenir vos relations sans en faire une liste
de corvées. Il retient qui compte pour vous et à quel rythme vous souhaitez
garder le contact, et vous propose chaque jour une poignée de personnes tout
au plus.

Ce manuel est généré à partir de l'aide intégrée à l'application. Les mêmes
textes y sont accessibles à tout moment avec **F1**.""",
}

TITEL = {"de": "Handbuch", "en": "Manual", "fr": "Manuel"}
INHALT = {"de": "Inhalt", "en": "Contents", "fr": "Sommaire"}
FUSSNOTE = {
    "de": ("Erzeugt aus der Hilfe der Anwendung mit `tools/build_handbook.py`. "
           "Aenderungen gehoeren in `freizeitmanager/i18n/de.json` unter `help.topics`."),
    "en": ("Generated from the application's help with `tools/build_handbook.py`. "
           "Edits belong in `freizeitmanager/i18n/en.json` under `help.topics`."),
    "fr": ("Généré à partir de l'aide de l'application avec `tools/build_handbook.py`. "
           "Les modifications vont dans `freizeitmanager/i18n/fr.json` sous `help.topics`."),
}
FUSSNOTE_HTML = {
    "de": "Erzeugt aus der Hilfe der Anwendung",
    "en": "Generated from the application's help",
    "fr": "Généré à partir de l'aide de l'application",
}

CSS = """
:root{color-scheme:light dark}
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.6;
max-width:52rem;margin:2rem auto;padding:0 1.5rem;color:#18202a;background:#fff}
h1{color:#0b7285;border-bottom:2px solid #0b7285;padding-bottom:.35rem;line-height:1.2}
h2{color:#0b7285;margin-top:2.2rem;line-height:1.3}
nav ul{padding-left:1.2rem}
nav a{color:#0b7285}
hr{border:0;border-top:1px solid #d9e0e5;margin:2rem 0}
footer{color:#5b6b7a;font-size:.9rem;margin-top:3rem}
@media(prefers-color-scheme:dark){
body{color:#e8edf2;background:#15191d}
h1,h2,nav a{color:#67c7d2}
footer{color:#94a3b1}}
""".strip()


def _topics(sprache: str = "de") -> tuple[str, list[tuple[str, str]]]:
    """Themen in der Reihenfolge der Oberflaeche, plus die Programmversion.

    Faellt ein Thema in einer Uebersetzung aus, gilt der deutsche Text. Ein
    fehlender Schluessel soll das Handbuch nicht zerreissen - eine Luecke faellt
    beim Lesen auf, ein Absturz des Release-Laufs waere unverhaeltnismaessig.
    """
    from freizeitmanager.app_info import APP_VERSION
    from freizeitmanager.ui.help_dialog import HELP_TOPICS

    def lade(name: str) -> dict:
        pfad = ROOT / "freizeitmanager" / "i18n" / f"{name}.json"
        return json.loads(pfad.read_text(encoding="utf-8"))["help"]["topics"]

    themen = lade(sprache)
    rueckfall = themen if sprache == "de" else lade("de")
    ausgabe = []
    for key in HELP_TOPICS:
        eintrag = themen.get(key) or rueckfall[key]
        ausgabe.append((eintrag["title"], eintrag["body"]))
    return APP_VERSION, ausgabe


# Deutsche Umlaute werden ausgeschrieben, alles andere - franzoesische
# Akzente etwa - auf den Grundbuchstaben zurueckgefuehrt. Ohne den zweiten
# Schritt wurde aus "Fraicheur" mit Zirkumflex ein "fra-cheur": der Verweis
# funktionierte zwar, weil beide Seiten denselben Weg nehmen, sah aber kaputt
# aus und konnte zwei aehnliche Titel zusammenfallen lassen.
_UMSCHRIFT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def _anchor(title: str) -> str:
    entfaltet = unicodedata.normalize("NFKD", title.lower().translate(_UMSCHRIFT))
    ohne_akzente = "".join(z for z in entfaltet if not unicodedata.combining(z))
    return re.sub(r"[^a-z0-9]+", "-", ohne_akzente).strip("-")


def markdown(version: str, topics: list[tuple[str, str]], sprache: str = "de") -> str:
    parts = [f"# FreizeitManager {version} \N{EN DASH} {TITEL[sprache]}", "",
             INTRO[sprache], "", f"## {INHALT[sprache]}", ""]
    parts += [f"- [{title}](#{_anchor(title)})" for title, _ in topics]
    for title, body in topics:
        parts += ["", f"## {title}", ""]
        # Die Hilfetexte tragen einfache HTML-Auszeichnung; fuer Markdown wird
        # daraus die uebliche Sternchenschreibweise.
        parts.append(body.replace("<b>", "**").replace("</b>", "**"))
    parts += ["", "---", "", FUSSNOTE[sprache]]
    return "\n".join(parts).strip() + "\n"


def page(version: str, topics: list[tuple[str, str]], sprache: str = "de") -> str:
    def paragraphs(body: str) -> str:
        out = []
        for block in body.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            # Nur <b> ist erlaubt - alles andere wird maskiert, damit ein
            # spitzes Klammerzeichen im Text die Seite nicht zerlegt.
            safe = html.escape(block).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
            out.append(f"<p>{safe}</p>")
        return "".join(out)

    toc = "".join(f'<li><a href="#{_anchor(t)}">{html.escape(t)}</a></li>' for t, _ in topics)
    body = "".join(f'<h2 id="{_anchor(t)}">{html.escape(t)}</h2>{paragraphs(b)}'
                   for t, b in topics)
    titel = f"FreizeitManager {html.escape(version)} \N{EN DASH} {TITEL[sprache]}"
    return (
        f'<!doctype html><html lang="{sprache}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{titel}</title>"
        f"<style>{CSS}</style></head><body>"
        f"<h1>{titel}</h1>"
        f"<nav><ul>{toc}</ul></nav>{body}"
        f"<footer>{FUSSNOTE_HTML[sprache]} "
        "(<code>tools/build_handbook.py</code>).</footer>"
        "</body></html>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="nur pruefen, ob die Dateien aktuell sind")
    args = parser.parse_args()

    wanted: dict[Path, str] = {}
    for sprache in SPRACHEN:
        version, topics = _topics(sprache)
        wanted[guide_pfad(sprache)] = markdown(version, topics, sprache)
        wanted[page_pfad(sprache)] = page(version, topics, sprache)

    if args.check:
        stale = [path for path, text in wanted.items()
                 if not path.is_file() or path.read_text(encoding="utf-8") != text]
        for path in stale:
            print(f"veraltet: {path.relative_to(ROOT)}", file=sys.stderr)
        if stale:
            print("Bitte 'python tools/build_handbook.py' ausfuehren.", file=sys.stderr)
            return 1
        print("Handbuch ist aktuell.")
        return 0

    for path, text in wanted.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"geschrieben: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
