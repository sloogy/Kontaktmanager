"""Wiederverwendbare Bausteine des Cockpits."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from freizeitmanager.logic import rotation_engine as rot
from freizeitmanager.ui import theme

# Beschriftung der Erledigt-Taste je Vorschlag. Ein Klick reicht - die
# Kontaktart steht schon fest, weil die Engine sie vorgeschlagen hat.
# Bewusst ohne Piktogramme: Symbole ausserhalb der Basisebene erscheinen je
# nach Systemschrift als leere Luecke. Die Karten tragen ihre Bedeutung im
# Text und im farbigen Ampelpunkt - das funktioniert auf jedem System.
DONE_LABELS = {
    rot.SUGGESTION_MEET: "Getroffen",
    rot.SUGGESTION_CALL: "Angerufen",
    rot.SUGGESTION_MESSAGE: "Geschrieben",
}

SNOOZE_OPTIONS = [("Diese Woche nicht", 7), ("Zwei Wochen Ruhe", 14),
                  ("Einen Monat pausieren", 30)]


class FocusTile(QFrame):
    """Kachel des Cockpits. Einfachklick filtert, Doppelklick oeffnet die Seite."""

    clicked = Signal(str)
    double_clicked = Signal(str)

    def __init__(self, key: str, title: str, accent: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.accent = accent
        self._selected = False
        self.setObjectName("focusTile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(92)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("tileTitle")
        self.value_label = QLabel("0")
        self.value_label.setObjectName("tileValue")
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("tileDetail")
        self.detail_label.setWordWrap(True)
        for label in (self.title_label, self.value_label, self.detail_label):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            layout.addWidget(label)
        layout.addStretch(1)

        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(lambda: self.clicked.emit(self.key))
        self._apply_style()

    def set_value(self, value: int, detail: str = "") -> None:
        self.value_label.setText(str(value))
        self.detail_label.setText(detail)

    def set_selected(self, selected: bool) -> None:
        if self._selected == bool(selected):
            return
        self._selected = bool(selected)
        self._apply_style()

    def _apply_style(self) -> None:
        border = self.accent if self._selected else "#dbe3ec"
        background = "#eff6ff" if self._selected else "#ffffff"
        self.setStyleSheet(
            f"QFrame#focusTile {{ background:{background}; border:2px solid {border};"
            f" border-radius:9px; }}"
            f"QLabel#tileTitle {{ color:{self.accent}; }}")

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.start(max(180, int(QApplication.doubleClickInterval())))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self.double_clicked.emit(self.key)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.key)
            event.accept()
            return
        super().keyPressEvent(event)


class NextStepCard(QFrame):
    """Eine konkrete naechste Handlung.

    Die Karte zeigt nie eine Punktzahl. Die Begruendung ist eingeklappt und
    nur auf Wunsch sichtbar - der Normalfall soll ruhig bleiben.
    """

    done = Signal(int, str)      # contact_id, interaction kind
    plan = Signal(int)
    snooze = Signal(int, int)    # contact_id, days
    wish = Signal(int)
    opened = Signal(int)

    def __init__(self, candidate: rot.Candidate, expert: bool = False, parent=None):
        super().__init__(parent)
        self.candidate = candidate
        self.setObjectName("stepCard")
        accent = theme.URGENCY_ACCENTS.get(candidate.urgency, theme.ACCENT_NEUTRAL)
        self.setStyleSheet(f"QFrame#stepCard {{ border-left: 5px solid {accent}; }}"
                           f"QLabel#stepUrgency {{ color: {accent}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 13, 16, 13)
        outer.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(8)
        dot = QLabel(candidate.icon)
        dot.setObjectName("stepDot")
        dot.setStyleSheet(f"color: {accent}; border: none;")
        name = QLabel(candidate.name)
        name.setObjectName("stepName")
        urgency = QLabel(rot.URGENCY_LABELS[candidate.urgency])
        urgency.setObjectName("stepUrgency")
        head.addWidget(dot)
        head.addWidget(name)
        head.addWidget(urgency)
        head.addStretch(1)
        outer.addLayout(head)

        suggestion = QLabel(f"{candidate.suggestion_text}"
                            f"  \N{MIDDLE DOT}  {candidate.suggestion_effort}")
        suggestion.setObjectName("stepSuggestion")
        outer.addWidget(suggestion)

        gap = QLabel(f"zuletzt {candidate.gap_text}")
        gap.setObjectName("stepGap")
        outer.addWidget(gap)

        self._why_button = QPushButton("Warum?")
        self._why_button.setObjectName("whyToggle")
        self._why_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._why_button.clicked.connect(self._toggle_why)
        outer.addWidget(self._why_button, 0, Qt.AlignmentFlag.AlignLeft)

        reasons = "\n".join(f"\N{BULLET} {r}" for r in candidate.why())
        if expert and candidate.breakdown:
            parts = ", ".join(f"{k} {v:g}" for k, v in candidate.breakdown.items() if v)
            reasons += f"\n\N{BULLET} intern: {candidate.score:g} ({parts})"
        self._why_label = QLabel(reasons)
        self._why_label.setObjectName("stepWhy")
        self._why_label.setWordWrap(True)
        self._why_label.setVisible(False)
        outer.addWidget(self._why_label)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        cid = candidate.contact_id

        done_btn = QPushButton(DONE_LABELS[candidate.suggestion])
        done_btn.setStyleSheet(theme.BTN_SUCCESS)
        done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        done_btn.setToolTip("Kontakt sofort eintragen - ohne Rueckfrage")
        done_btn.clicked.connect(
            lambda: self.done.emit(cid, rot.SUGGESTION_TO_KIND[candidate.suggestion]))

        plan_btn = QPushButton("Planen")
        plan_btn.setStyleSheet(theme.BTN_SECONDARY)
        plan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        plan_btn.clicked.connect(lambda: self.plan.emit(cid))

        later_btn = QPushButton("Sp\N{LATIN SMALL LETTER A WITH DIAERESIS}ter")
        later_btn.setStyleSheet(theme.BTN_QUIET)
        later_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        later_btn.clicked.connect(lambda: self._later_menu(later_btn))

        for button in (done_btn, plan_btn, later_btn):
            actions.addWidget(button)
        actions.addStretch(1)

        open_btn = QPushButton("\N{RIGHTWARDS ARROW} Kontakt")
        open_btn.setStyleSheet(theme.BTN_QUIET)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(lambda: self.opened.emit(cid))
        actions.addWidget(open_btn)
        outer.addLayout(actions)

    def _toggle_why(self) -> None:
        visible = not self._why_label.isVisible()
        self._why_label.setVisible(visible)
        self._why_button.setText("Warum? \N{UPWARDS ARROW}" if visible else "Warum?")

    def _later_menu(self, anchor: QPushButton) -> None:
        menu = QMenu(self)
        actions = {menu.addAction(label): days for label, days in SNOOZE_OPTIONS}
        menu.addSeparator()
        wish_action = menu.addAction("Im Gegenteil: m\N{LATIN SMALL LETTER O WITH DIAERESIS}chte ich bald sehen")
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen is None:
            return
        if chosen is wish_action:
            self.wish.emit(self.candidate.contact_id)
        else:
            self.snooze.emit(self.candidate.contact_id, actions[chosen])


class CalmCard(QFrame):
    """Ruhiger Zustand - ersetzt jede leere Tabelle."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("calmCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        label = QLabel(text)
        label.setObjectName("calmText")
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch(1)
