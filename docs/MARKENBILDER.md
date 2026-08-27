# Markenbilder des FreizeitManagers

## Woher sie stammen

Im Repo liegen zwei unskalierte Quellbilder aus der Bildmappe der Suite:

```
freizeitmanager/resources/icons/freizeitmanager-source.png        1254 x 1254, RGBA
freizeitmanager/resources/icons/freizeitmanager-logo-source.png   2172 x  724, RGBA
```

Sie sind Teil des Programms, kein Build-Artefakt: nur so bleibt jede Ausgabe
reproduzierbar erzeugbar, ohne dass eine externe Datei zur Hand sein muss.
Ins Paket wandern sie nicht — sie wuerden es um rund 800 kB vergroessern,
ohne je gelesen zu werden.

**Ausgeliefert wird keines von beiden direkt.** Beide tragen ungleiche
unsichtbare Raender — beim Banner 25 Bildpunkte links und 88 rechts, 27 oben
und 52 unten. Ein solches Bild in einer Flaeche fester Breite wirkt zu klein
und rutscht sichtbar aus der Mitte, obwohl das Layout korrekt zentriert.
Zusaetzlich liegt ueber dem ganzen Blatt ein Schleier mit Alpha 1 bis 3:
unsichtbar, aber fuer jede Randmessung gegen Null deckend.
`tools/create_icons.py` misst deshalb gegen eine Alphaschwelle von 8 und

* schneidet beim **Banner** die unsichtbaren Raender weg — danach ist die
  Bildkante die Motivkante,
* setzt das **Icon-Motiv** mittig auf ein transparentes Quadrat mit 2 % Rand
  je Seite. Randlos darf ein Icon nicht sein (in 16 px klebt es sonst an der
  Kante), aber der Rand muss ringsum gleich sein, sonst haengt das Symbol
  neben anderen Symbolen sichtbar schief.

---

## Neu erzeugen

Voraussetzung ist Pillow (nur fuer dieses Werkzeug, keine
Laufzeit-Abhaengigkeit des Programms):

```bash
pip install Pillow
python tools/create_icons.py
```

Das Skript schreibt nach `freizeitmanager/resources/icons/`:

| Datei | Inhalt |
|---|---|
| `freizeitmanager-{16,32,48,64,128,256,512}.png` | Einzelgroessen fuer Qt und die Linux-Desktops |
| `freizeitmanager.png` | 1024 px, generisches Programmsymbol |
| `freizeitmanager.ico` | Mehrfachaufloesung 16/24/32/48/64/128/256 px, Windows |
| `freizeitmanager-logo.png` | Banner fuer helle Flaechen |
| `freizeitmanager-logo-hell.png` | Dieselbe Zeichnung fuer dunkle Flaechen |

---

## Warum es das Banner zweimal gibt

Der Schriftzug ist zur Haelfte dunkelblau (`#0D1B3A`). Auf hellem Grund ist
das richtig; die Seitenleisten der dunklen Profile gehen bis `#050505`, dort
waere das halbe Wort weg. Die zweite Fassung faerbt Dunkelblau nach Weiss und
hellt Petrol und Gruen auf; zugeordnet wird ueber den naechstliegenden der
vier Flaechenfarben der Bildmappe.

Welche Fassung erscheint, entscheidet `freizeitmanager/ui/branding.py` und
nicht die Aufrufstelle — sonst muesste jede Stelle dieselbe
Fallunterscheidung noch einmal treffen und eine wuerde sie vergessen.
Gefragt wird die Farbe der **konkreten Flaeche** aus dem aktiven Profil, nicht
dessen Hell/Dunkel-Kennzeichen: Die Seitenleiste ist eine eigene Farbe, und
ein Profil koennte dort dunkel werden, ohne insgesamt dunkel zu sein.

---

## Wo sie eingebunden sind

| Ort | Verwendung |
|---|---|
| `main.py` | Fenster-/Taskleistensymbol, Startbildschirm vor dem Laden der Datenbank |
| `freizeitmanager/ui/main_window.py` | Banner in der Seitenleiste, statt der frueheren Textzeile |
| `freizeitmanager/ui/menu_bar.py` | Quadratisches Symbol im Ueber-Dialog |
| `FreizeitManager.spec` | `icon=` fuer Windows, und alle `.png`/`.ico` als Daten im Paket |
| `main.py --smoke` | Meldet fehlende Bilder im gebauten Paket als Fehler |

Der letzte Punkt ist der wichtigste: Die Bilder werden ueber den Dateipfad
geladen und nicht importiert. PyInstaller findet sie nur, weil die `.spec`
sie auffuehrt — faellt der Eintrag weg, startet das gebaute Programm ohne
Symbol und ohne Startbildschirm, und ohne den Selbsttest merkt das niemand
vor der Auslieferung.

---

## Warum der Startbildschirm nicht einfach stehen bleibt

Zwischen Programmstart und Hauptfenster legt die Datenbank ihr Schema an,
migriert, laedt die Sprache und uebernimmt beim allerersten Start den alten
Kontaktmanager-Bestand. Ein Splash, der stumpf bis zum Hauptfenster stehen
bliebe, wuerde ueber jedem Hinweis kleben, den der Start zeigen will — das
waere schlimmer als gar keiner.

`freizeitmanager/ui/startup_splash.py` beobachtet deshalb die Anwendung:
Sobald ein modales Fenster sichtbar wird, verschwindet der Splash; ist das
letzte wieder zu, kommt er zurueck. Zwei Notbremsen sichern ab, dass er nie
haengen bleibt — ein Watchdog nach 30 Sekunden und `close_active()`, das aus
jedem Fehlerpfad ohne Referenz aufrufbar ist.

---

## Troubleshooting

| Problem | Loesung |
|---|---|
| `ModuleNotFoundError: PIL` | `pip install Pillow` |
| `Quellbild fehlt: ...-source.png` | Aus der Versionsgeschichte zurueckholen |
| Banner sitzt schief oder wirkt zu klein | `python tools/create_icons.py` erneut laufen lassen; vermutlich liegt eine unbeschnittene Quelldatei als `freizeitmanager-logo.png` im Ordner |
| Halbes Wort auf dunklem Grund unsichtbar | `freizeitmanager-logo-hell.png` fehlt oder ist eine Kopie der dunklen Fassung |
