"""Menüleiste des Hauptfensters – Aufbau nach der BudgetManager-Vorlage.

Der FreizeitManager hatte bis Loop 33 keine, genau wie FPM bis Loop 32:
Alles lief über Seitenleiste und Tastenkürzel. Für sich genommen bedienbar,
aber der BudgetManager ist die Design-Vorlage der Suite, und dort gibt es
Datei / Ansicht / Extras / Hilfe. Wer zwischen den Programmen wechselt,
sucht sonst an einer Stelle, die es hier nicht gibt.

Übernommen sind auch die Richtlinien, die der BudgetManager in
``views/help_menu.py`` festhält (GNOME HIG, Windows App Design, Apple HIG):
kurz halten, mit Trennlinien gruppieren, ``…`` nur vor Befehlen mit
Rückfrage und immer als ein Zeichen, eindeutige Zugriffstasten je Menü,
„Über" zuletzt.

Die Leiste ersetzt nichts. Die Seitenleiste bleibt, wo sie ist, und die
Kürzel gelten weiter: Wer den FreizeitManager kennt, soll nach dem Update
nicht umlernen müssen.

Zur Lebensdauer: ``QMenuBar.addMenu`` gibt in PySide6 eine Hülle zurück, die
Python gehört – fällt der letzte Verweis, nimmt sie das Menü mit. Darum hält
das Fenster seine Menüs in ``_menus`` fest. Im laufenden Programm fällt das
nie auf, unter pytest sofort (siehe FPM, Loop 32).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QMenuBar

from freizeitmanager.i18n.translator import t


def _eintrag(menu, fenster, text: str, callback, *, kuerzel: str = "", tip: str = ""):
    """Ein Menüeintrag mit Zugriffstaste, Kürzel und Statuszeilentext."""
    aktion = QAction(text, fenster)
    if kuerzel:
        aktion.setShortcut(QKeySequence(kuerzel))
        # Ohne diesen Kontext feuert das Kürzel nur, solange das Menü offen
        # ist - also nie.
        aktion.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
    if tip:
        aktion.setStatusTip(tip)
    aktion.triggered.connect(callback)
    menu.addAction(aktion)
    return aktion


def build_menu_bar(fenster) -> QMenuBar:
    """Baut die Menüleiste des Hauptfensters auf und gibt sie zurück."""
    leiste = fenster.menuBar()
    leiste.clear()
    fenster._menu_bar = leiste
    fenster._menus = [
        _datei_menu(leiste, fenster),
        _ansicht_menu(leiste, fenster),
        _extras_menu(leiste, fenster),
        _hilfe_menu(leiste, fenster),
    ]
    return leiste


def _datei_menu(leiste: QMenuBar, fenster):
    menu = leiste.addMenu(t("menu.file"))
    _eintrag(menu, fenster, t("menu.settings"),
             lambda: fenster.show_page("settings"), tip=t("menu.settings_tip"))
    _eintrag(menu, fenster, t("menu.open_data_folder"),
             lambda: _datenordner_oeffnen(fenster),
             tip=t("menu.open_data_folder_tip"))
    menu.addSeparator()
    _eintrag(menu, fenster, t("menu.exit"), fenster.close,
             kuerzel="Ctrl+Q", tip=t("menu.exit_tip"))
    return menu


def _ansicht_menu(leiste: QMenuBar, fenster):
    from freizeitmanager.ui.main_window import PAGES

    menu = leiste.addMenu(t("menu.view"))

    seiten = menu.addMenu(t("menu.pages"))
    # Dieselbe Reihenfolge wie in der Seitenleiste: Das Menue ist eine zweite
    # Tuer zum selben Raum, keine eigene Ordnung.
    fenster._menu_page_actions = {}
    for schluessel, titel_key, nur_experte in PAGES:
        aktion = QAction(t(titel_key), fenster)
        aktion.triggered.connect(lambda _=False, k=schluessel: fenster.show_page(k))
        seiten.addAction(aktion)
        # Expertenseiten sind im Einfachmodus auch hier nicht erreichbar -
        # sonst fuehrt das Menue auf eine Seite, die die Seitenleiste
        # ausdruecklich versteckt.
        aktion.setProperty("nur_experte", nur_experte)
        fenster._menu_page_actions[schluessel] = aktion

    menu.addSeparator()

    modus = menu.addMenu(t("menu.mode"))
    gruppe = QActionGroup(fenster)
    gruppe.setExclusive(True)
    fenster._menu_mode_actions = {}
    for experte, schluessel in ((False, "menu.mode_simple"), (True, "menu.mode_expert")):
        aktion = QAction(t(schluessel), fenster)
        aktion.setCheckable(True)
        aktion.triggered.connect(lambda _=False, e=experte: _modus_setzen(fenster, e))
        gruppe.addAction(aktion)
        modus.addAction(aktion)
        fenster._menu_mode_actions[experte] = aktion

    menu.addSeparator()

    vollbild = QAction(t("menu.fullscreen"), fenster)
    vollbild.setCheckable(True)
    vollbild.setShortcut(QKeySequence("F11"))
    vollbild.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
    vollbild.setStatusTip(t("menu.fullscreen_tip"))
    vollbild.triggered.connect(lambda an: _vollbild(fenster, an))
    menu.addAction(vollbild)
    fenster._menu_fullscreen_action = vollbild
    fenster._menu_pages = seiten
    fenster._menu_mode = modus
    return menu


def _extras_menu(leiste: QMenuBar, fenster):
    """Dieselben Befehle, die schon auf Kürzeln liegen.

    Ein Kürzel, das nirgends geschrieben steht, kennt nur, wer es kennt. Das
    Menü ist die auffindbare Seite derselben Sache.
    """
    menu = leiste.addMenu(t("menu.extras"))
    _eintrag(menu, fenster, t("menu.add_contact"),
             lambda: _kontakt_anlegen(fenster), kuerzel="Ctrl+N",
             tip=t("menu.add_contact_tip"))
    menu.addSeparator()
    _eintrag(menu, fenster, t("menu.toggle_mode"), fenster._toggle_mode,
             kuerzel="Ctrl+E", tip=t("menu.toggle_mode_tip"))
    return menu


def _hilfe_menu(leiste: QMenuBar, fenster):
    menu = leiste.addMenu(t("menu.help"))
    _eintrag(menu, fenster, t("menu.manual"), lambda: fenster.open_help(),
             kuerzel="F1", tip=t("menu.manual_tip"))
    menu.addSeparator()
    # Ueber steht zuletzt
    _eintrag(menu, fenster, t("menu.about"), lambda: _ueber_zeigen(fenster))
    return menu


def _ueber_zeigen(fenster) -> None:
    """Name, Version und Datenordner.

    Im FreizeitManager standen diese Angaben bisher nirgends in der
    Oberflaeche - anders als in FPM, wo die Einstellungen eine Ueber-Seite
    haben. Wer wissen wollte, welche Fassung laeuft, musste raten.
    """
    from PySide6.QtWidgets import QMessageBox

    from freizeitmanager.app_info import APP_NAME, APP_VERSION
    from freizeitmanager.paths import data_dir
    from freizeitmanager.ui.branding import icon_pixmap

    dialog = QMessageBox(fenster)
    dialog.setWindowTitle(t("menu.about_title"))
    dialog.setText(f"{APP_NAME} {APP_VERSION}\n\n{t('menu.about_data')}\n{data_dir()}")
    # An dieser Stelle das quadratische Programmsymbol und nicht das breite
    # Banner: QMessageBox stellt links eine quadratische Flaeche bereit und
    # zieht den Text daneben. Ein dreimal so breites Bild wuerde den Dialog
    # entweder auseinanderziehen oder gestaucht wirken.
    symbol = icon_pixmap(64, device_pixel_ratio=fenster.devicePixelRatioF())
    if symbol is not None:
        dialog.setIconPixmap(symbol)
    else:
        dialog.setIcon(QMessageBox.Icon.Information)
    dialog.exec()


def _vollbild(fenster, an: bool) -> None:
    if an:
        fenster.showFullScreen()
    else:
        fenster.showNormal()


def _modus_setzen(fenster, experte: bool) -> None:
    """Setzt den Modus, statt ihn nur umzuschalten.

    Das Menue nennt beide Zustaende beim Namen; ein Umschalter wuerde beim
    Klick auf den bereits aktiven in den anderen springen.
    """
    if fenster._expert != experte:
        fenster._toggle_mode()
    sync_menu_state(fenster)


def _kontakt_anlegen(fenster) -> None:
    fenster.show_page("contacts")
    fenster._contacts._create()


def _datenordner_oeffnen(fenster) -> None:
    from freizeitmanager.paths import data_dir
    from freizeitmanager.ui.common import open_in_file_manager

    open_in_file_manager(fenster, data_dir())


def sync_menu_state(fenster) -> None:
    """Hält Häkchen und Sichtbarkeit mit dem tatsächlichen Zustand gleich.

    Der Modusumschalter sitzt jetzt an drei Stellen - Seitenleiste, Kürzel,
    Menü. Zeigen sie Verschiedenes, ist einer davon falsch, und der Nutzer
    glaubt dem, den er zuerst sieht.
    """
    aktionen = getattr(fenster, "_menu_mode_actions", None)
    if aktionen:
        for experte, aktion in aktionen.items():
            aktion.setChecked(experte == fenster._expert)
    seiten = getattr(fenster, "_menu_page_actions", None)
    if seiten:
        for aktion in seiten.values():
            nur_experte = bool(aktion.property("nur_experte"))
            aktion.setVisible(fenster._expert or not nur_experte)
    vollbild = getattr(fenster, "_menu_fullscreen_action", None)
    if vollbild is not None:
        vollbild.setChecked(fenster.isFullScreen())


__all__ = ["build_menu_bar", "sync_menu_state"]
