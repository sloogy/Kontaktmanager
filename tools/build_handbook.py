#!/usr/bin/env python3
"""Baut Handbuch und Hilfeseite aus den Texten der In-App-Hilfe.

Bewusst eine einzige Quelle: Die Hilfethemen stehen in ``i18n/de.json`` unter
``help.topics`` und werden dort gepflegt. Ein zweiter, von Hand gefuehrter
Handbuchtext wuerde binnen zweier Releases davon abweichen - im BudgetManager
war genau das der Grund, die Hilfe generieren zu lassen.

    python tools/build_handbook.py [--check]

``--check`` schreibt nichts und meldet mit Exitcode 1, wenn die erzeugten
Dateien nicht mehr zum Stand der Sprachdatei passen.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GUIDE = ROOT / "docs" / "USER_GUIDE.de.md"
PAGE = ROOT / "docs" / "help" / "index.html"

INTRO = """Der FreizeitManager hilft dabei, Beziehungen zu pflegen, ohne daraus eine
Pflichtenliste zu machen. Er merkt sich, wer wie wichtig ist und in welchem
Rhythmus Kontakt gewuenscht ist, und schlaegt taeglich hoechstens eine Handvoll
Menschen vor.

Dieses Handbuch wird aus der Hilfe in der Anwendung erzeugt. Dieselben Texte
erreichen Sie dort jederzeit mit **F1**."""

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


def _topics() -> tuple[str, list[tuple[str, str]]]:
    """Themen in der Reihenfolge der Oberflaeche, plus die Programmversion."""
    from freizeitmanager.app_info import APP_VERSION
    from freizeitmanager.ui.help_dialog import HELP_TOPICS

    data = json.loads((ROOT / "freizeitmanager" / "i18n" / "de.json").read_text(encoding="utf-8"))
    topics = data["help"]["topics"]
    return APP_VERSION, [(topics[key]["title"], topics[key]["body"]) for key in HELP_TOPICS]


def _anchor(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower().replace("ä", "ae").replace("ö", "oe")
                  .replace("ü", "ue").replace("ß", "ss"))
    return slug.strip("-")


def markdown(version: str, topics: list[tuple[str, str]]) -> str:
    parts = [f"# FreizeitManager {version} \N{EN DASH} Handbuch", "", INTRO, "", "## Inhalt", ""]
    parts += [f"- [{title}](#{_anchor(title)})" for title, _ in topics]
    for title, body in topics:
        parts += ["", f"## {title}", ""]
        # Die Hilfetexte tragen einfache HTML-Auszeichnung; fuer Markdown wird
        # daraus die uebliche Sternchenschreibweise.
        parts.append(body.replace("<b>", "**").replace("</b>", "**"))
    parts += ["", "---", "",
              "Erzeugt aus der Hilfe der Anwendung mit `tools/build_handbook.py`. "
              "Aenderungen gehoeren in `freizeitmanager/i18n/de.json` unter `help.topics`."]
    return "\n".join(parts).strip() + "\n"


def page(version: str, topics: list[tuple[str, str]]) -> str:
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
    return (
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>FreizeitManager {html.escape(version)} \N{EN DASH} Handbuch</title>"
        f"<style>{CSS}</style></head><body>"
        f"<h1>FreizeitManager {html.escape(version)} \N{EN DASH} Handbuch</h1>"
        f"<nav><ul>{toc}</ul></nav>{body}"
        "<footer>Erzeugt aus der Hilfe der Anwendung "
        "(<code>tools/build_handbook.py</code>).</footer>"
        "</body></html>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="nur pruefen, ob die Dateien aktuell sind")
    args = parser.parse_args()

    version, topics = _topics()
    wanted = {GUIDE: markdown(version, topics), PAGE: page(version, topics)}

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
