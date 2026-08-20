"""Hilfe in der Anwendung: Themen links, Text rechts, Suche darueber.

Bewusst themenbasiert und nicht als ein langer Fliesstext: Wer Hilfe oeffnet,
sucht eine Antwort, nicht eine Lektuere. Das vollstaendige Handbuch liegt
daneben und wird ueber den Knopf im Browser geoeffnet.

Die Texte stehen in den Sprachdateien unter ``help.topics``. Damit folgt die
Hilfe der gewaehlten Sprache wie jeder andere Text auch.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from freizeitmanager.i18n.translator import t
from freizeitmanager.ui import theme

# Reihenfolge ist Absicht: vom Erststart zum Alltag, Randthemen zuletzt.
HELP_TOPICS = (
    "first_steps",
    "import",
    "cockpit",
    "contacts",
    "logging",
    "freshness",
    "birthdays",
    "activities",
    "modes",
    "settings",
)


def handbook_path() -> Path | None:
    """Das gebaute Handbuch - im Quellbaum wie im gepackten Programm."""
    candidates = []
    bundle = getattr(sys, "_MEIPASS", "")
    if bundle:
        candidates.append(Path(bundle) / "docs" / "help" / "index.html")
    candidates.append(Path(__file__).resolve().parents[2] / "docs" / "help" / "index.html")
    return next((path for path in candidates if path.is_file()), None)


def topic_text(key: str) -> tuple[str, str]:
    return t(f"help.topics.{key}.title"), t(f"help.topics.{key}.body")


def matches(key: str, needle: str) -> bool:
    """Sucht in Titel und Text - eine Suche nur ueber Titel fände zu wenig."""
    if not needle:
        return True
    title, body = topic_text(key)
    return needle.lower() in f"{title}\n{body}".lower()


class HelpDialog(QDialog):
    """Themenhilfe. Wird ueber F1 oder den Knopf in der Seitenleiste geoeffnet."""

    def __init__(self, topic: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("help.title"))
        self.setMinimumSize(780, 540)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("help.search"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        body = QHBoxLayout()
        body.setSpacing(12)
        self._topics = QListWidget()
        self._topics.setMaximumWidth(240)
        self._topics.currentItemChanged.connect(self._show_current)
        body.addWidget(self._topics)

        self._text = QTextBrowser()
        self._text.setOpenExternalLinks(True)
        body.addWidget(self._text, 1)
        layout.addLayout(body)

        self._empty = QLabel(t("help.no_match"))
        self._empty.setObjectName("pageHint")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setVisible(False)
        layout.addWidget(self._empty)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        self._handbook = QPushButton(t("help.handbook"))
        self._handbook.setStyleSheet(theme.btn_quiet())
        self._handbook.setCursor(Qt.CursorShape.PointingHandCursor)
        self._handbook.clicked.connect(self._open_handbook)
        # Ein Knopf, der ins Leere fuehrt, ist schlimmer als keiner.
        self._handbook.setEnabled(handbook_path() is not None)
        if handbook_path() is None:
            self._handbook.setToolTip(t("help.handbook_missing"))
        buttons.addButton(self._handbook, QDialogButtonBox.ButtonRole.ActionRole)
        layout.addWidget(buttons)

        self._fill()
        self.show_topic(topic or HELP_TOPICS[0])

    def _fill(self, needle: str = "") -> None:
        self._topics.clear()
        for key in HELP_TOPICS:
            if not matches(key, needle):
                continue
            item = QListWidgetItem(topic_text(key)[0])
            item.setData(Qt.ItemDataRole.UserRole, key)
            self._topics.addItem(item)
        found = self._topics.count() > 0
        self._topics.setVisible(found)
        self._text.setVisible(found)
        self._empty.setVisible(not found)
        if found:
            self._topics.setCurrentRow(0)

    def _filter(self, needle: str) -> None:
        self._fill(needle.strip())

    def _show_current(self, current, _previous=None) -> None:
        if current is None:
            return
        title, text = topic_text(str(current.data(Qt.ItemDataRole.UserRole)))
        paragraphs = "".join(f"<p>{line}</p>" for line in text.split("\n\n") if line.strip())
        self._text.setHtml(f"<h2>{title}</h2>{paragraphs}")

    def show_topic(self, key: str) -> bool:
        """Springt auf ein Thema; ``False``, wenn es das Thema nicht gibt."""
        for row in range(self._topics.count()):
            if self._topics.item(row).data(Qt.ItemDataRole.UserRole) == key:
                self._topics.setCurrentRow(row)
                return True
        return False

    def current_topic(self) -> str | None:
        item = self._topics.currentItem()
        return None if item is None else str(item.data(Qt.ItemDataRole.UserRole))

    def _open_handbook(self) -> None:
        path = handbook_path()
        if path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
