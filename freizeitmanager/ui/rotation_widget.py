"""Rotationsuebersicht - Expertenbereich.

Hier und nur hier wird die Punktzahl sichtbar. Der Bildschirm existiert, damit
die Engine nachvollziehbar bleibt, nicht fuer den Alltag.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from freizeitmanager.database import db
from freizeitmanager.logic import rotation_engine as rot
from freizeitmanager.logic.event_bus import AppEventBus

COLUMNS = ["", "Name", "Zustand", "Vorschlag", "Zuletzt", "Faktor", "Score", "Begruendung"]


class RotationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 22)
        layout.setSpacing(10)

        title = QLabel("Rotation")
        title.setObjectName("pageTitle")
        hint = QLabel("Vollstaendige Bewertung aller Kontakte. Der Alltag braucht diesen "
                      "Bildschirm nicht - er macht die Engine pruefbar.")
        hint.setObjectName("pageHint")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(len(COLUMNS) - 1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

        AppEventBus.instance().focus_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        with db.get_session() as session:
            candidates = rot.evaluate_all(session)
        self._table.setRowCount(len(candidates))
        for row, cand in enumerate(candidates):
            state = cand.reasons[0] if cand.blocks else rot.URGENCY_LABELS[cand.urgency]
            values = [
                cand.icon, cand.name, state,
                cand.suggestion_text,
                cand.gap_text,
                f"{cand.freshness.overdue_ratio:g}\N{MULTIPLICATION SIGN}",
                f"{cand.score:g}",
                " \N{MIDDLE DOT} ".join(cand.why()),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in (0, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 6:
                    item.setToolTip(", ".join(f"{k}: {v:g}" for k, v in cand.breakdown.items()))
                self._table.setItem(row, column, item)
