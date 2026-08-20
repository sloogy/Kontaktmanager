"""Hauptfenster mit Sidebar und Einfach-/Expertenmodus.

Der FreizeitManager startet bewusst im Einfachmodus (Lehre aus FPM 0.2.76):
Cockpit und Kontakte reichen fuer den Alltag. Die pruefbaren und
konfigurierbaren Teile bleiben erhalten, nur nicht im Weg.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from freizeitmanager.app_info import APP_NAME, APP_VERSION
from freizeitmanager.database import db
from freizeitmanager.i18n.translator import load_language_from_settings, t
from freizeitmanager.logic.event_bus import AppEventBus
from freizeitmanager.ui.contacts_widget import ContactsWidget
from freizeitmanager.ui.dashboard_widget import DashboardWidget
from freizeitmanager.ui.rotation_widget import RotationWidget
from freizeitmanager.ui.settings_widget import SettingsWidget
from freizeitmanager.ui.styles import get_stylesheet, install_emoji_fallback
from freizeitmanager.ui.theme_manager import ThemeManager

# key, Uebersetzungsschluessel, nur im Expertenmodus
PAGES = [
    ("cockpit", "nav.cockpit", False),
    ("contacts", "nav.contacts", False),
    ("rotation", "nav.rotation", True),
    ("settings", "nav.settings", False),
]


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1180, 780)
        self.setMinimumSize(720, 560)
        install_emoji_fallback()
        self._apply_theme()

        load_language_from_settings()
        with db.get_session() as session:
            self._expert = db.get_setting(session, "ui.mode", "simple") == "expert"

        central = QWidget()
        self.setCentralWidget(central)
        from PySide6.QtWidgets import QHBoxLayout
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        self._pages: dict[str, QWidget] = {}
        self._dashboard = DashboardWidget(expert=self._expert)
        self._contacts = ContactsWidget(expert=self._expert)
        self._rotation = RotationWidget()
        self._settings = SettingsWidget()
        for key, widget in (("cockpit", self._dashboard), ("contacts", self._contacts),
                            ("rotation", self._rotation), ("settings", self._settings)):
            self._pages[key] = widget
            self._stack.addWidget(widget)

        self._dashboard.navigate_to.connect(self.show_page)
        self._dashboard.open_contact.connect(self._open_contact)

        QShortcut(QKeySequence("Ctrl+N"), self, self._contacts._create)
        QShortcut(QKeySequence("Ctrl+E"), self, self._toggle_mode)
        QShortcut(QKeySequence("F1"), self, self.open_help)

        bus = AppEventBus.instance()
        bus.language_changed.connect(self._rebuild_for_language)
        bus.theme_changed.connect(self._apply_theme)
        self._apply_mode()
        self.show_page("cockpit")

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        logo = QLabel(APP_NAME)
        logo.setObjectName("sidebarLogo")
        layout.addWidget(logo)

        self._nav_buttons: dict[str, QPushButton] = {}
        for key, label_key, _expert_only in PAGES:
            button = QPushButton(t(label_key))
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, k=key: self.show_page(k))
            self._nav_buttons[key] = button
            layout.addWidget(button)

        layout.addStretch(1)
        self._help_button = QPushButton(t("help.button"))
        self._help_button.setObjectName("navButton")
        self._help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._help_button.clicked.connect(self.open_help)
        layout.addWidget(self._help_button)

        self._mode_button = QPushButton("")
        self._mode_button.setObjectName("modeToggle")
        self._mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_button.clicked.connect(self._toggle_mode)
        layout.addWidget(self._mode_button)

        version = QLabel(t("app.version", version=APP_VERSION))
        version.setObjectName("sidebarVersion")
        layout.addWidget(version)
        return sidebar

    def _apply_theme(self) -> None:
        """Stylesheet neu setzen und die Schrift der Anwendung angleichen.

        Die Schriftgroesse muss zusaetzlich am QApplication-Font haengen,
        sonst rechnen Tabellen ihre Zeilenhoehen weiter mit der alten Groesse.
        """
        from PySide6.QtWidgets import QApplication
        ThemeManager.reset()
        profile = ThemeManager.instance().current_profile()
        self.setStyleSheet(get_stylesheet(1.0, profile))
        app = QApplication.instance()
        if app is not None:
            font = app.font()
            font.setPointSize(profile.font_size)
            app.setFont(font)
        # Kacheln und Karten setzen ihre Farben als Inline-Stylesheet, das das
        # Anwendungs-Stylesheet ueberschreibt. Ein refresh() erneuert nur den
        # Inhalt, nicht den Stil - deshalb werden die Seiten neu aufgebaut.
        if getattr(self, "_pages", None):
            self._rebuild_pages()

    def _rebuild_for_language(self) -> None:
        """Sprache wechseln: Beschriftungen der Navigation und alle Seiten.

        Qt uebersetzt gesetzte Beschriftungen nicht nachtraeglich. Ein
        Neuaufbau ist hier ehrlicher als hunderte setText-Aufrufe zu pflegen,
        von denen frueher oder spaeter einer vergessen wird.
        """
        for key, label_key, _ in PAGES:
            self._nav_buttons[key].setText(t(label_key))
        self._help_button.setText(t("help.button"))
        self._rebuild_pages()

    def _rebuild_pages(self) -> None:
        """Alle Seiten neu erzeugen und die aktive Seite beibehalten."""
        current = next((key for key, button in self._nav_buttons.items()
                        if button.isChecked()), "cockpit")

        for key, factory in (("cockpit", lambda: DashboardWidget(expert=self._expert)),
                             ("contacts", lambda: ContactsWidget(expert=self._expert)),
                             ("rotation", RotationWidget),
                             ("settings", SettingsWidget)):
            old = self._pages[key]
            new = factory()
            self._stack.insertWidget(self._stack.indexOf(old), new)
            self._stack.removeWidget(old)
            old.deleteLater()
            self._pages[key] = new

        self._dashboard = self._pages["cockpit"]
        self._contacts = self._pages["contacts"]
        self._rotation = self._pages["rotation"]
        self._settings = self._pages["settings"]
        self._dashboard.navigate_to.connect(self.show_page)
        self._dashboard.open_contact.connect(self._open_contact)
        self._apply_mode()
        self.show_page(current)

    def open_help(self, topic: str | None = None) -> None:
        """F1 und der Knopf in der Seitenleiste fuehren an dieselbe Stelle."""
        from freizeitmanager.ui.help_dialog import HelpDialog
        HelpDialog(topic, self).exec()

    def show_page(self, key: str) -> None:
        widget = self._pages.get(key)
        if widget is None:
            return
        self._stack.setCurrentWidget(widget)
        for name, button in self._nav_buttons.items():
            button.setChecked(name == key)

    def _open_contact(self, contact_id: int) -> None:
        self.show_page("contacts")
        self._contacts.select_contact(contact_id)

    def _toggle_mode(self) -> None:
        self._expert = not self._expert
        with db.get_session() as session:
            db.set_setting(session, "ui.mode", "expert" if self._expert else "simple")
        self._apply_mode()

    def _apply_mode(self) -> None:
        for key, _label, expert_only in PAGES:
            self._nav_buttons[key].setVisible(self._expert or not expert_only)
        self._mode_button.setText(
            "\N{LEFTWARDS ARROW} " + t("nav.simple_mode") if self._expert
            else t("nav.expert_mode") + " \N{RIGHTWARDS ARROW}")
        self._dashboard.set_expert(self._expert)
        self._contacts.set_expert(self._expert)
        if not self._expert and self._stack.currentWidget() is self._rotation:
            self.show_page("cockpit")
