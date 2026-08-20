"""Fokus-Cockpit.

Vorbild BudgetManager: Der Startbildschirm beantwortet "was ist jetzt dran?".
Vorbild FPM: responsive Kacheln, im Grundzustand keine Detailtabellen, und
statt einer leeren Tabelle eine kompakte Entwarnung.

Alles Zaehlbare steht in vier Kacheln, alles Handlungsrelevante in maximal
drei Karten. Mehr bekommt dieser Bildschirm nicht - unabhaengig davon,
wie viele Kandidaten die Engine kennt.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from freizeitmanager.database import db
from freizeitmanager.database.models import Contact
from freizeitmanager.i18n.translator import t
from freizeitmanager.integration import lifeplanner_bridge as bridge
from freizeitmanager.logic import contact_service as cs
from freizeitmanager.logic import dashboard_service as dash
from freizeitmanager.logic import rotation_engine as rot
from freizeitmanager.logic.event_bus import AppEventBus
from freizeitmanager.ui import theme
from freizeitmanager.ui.common import CalmCard, FocusTile, NextStepCard
from freizeitmanager.ui.dialogs import PlanActivityDialog

# Schluessel statt Text - die Beschriftung entsteht erst beim Aufbau.
# Schluessel und Dringlichkeitsstufe - Farbe und Text entstehen erst beim
# Aufbau, damit Theme- und Sprachwechsel sofort greifen.
TILE_SPECS = [
    ("due_now", "cockpit.tile_due", "due"),
    ("this_week", "cockpit.tile_week", "soon"),
    ("planned", "cockpit.tile_planned", "planned"),
    ("all_good", "cockpit.tile_good", "fresh"),
]

ENERGY_SPECS = [
    (rot.ENERGY_LOW, "cockpit.energy_low"),
    (rot.ENERGY_NORMAL, "cockpit.energy_normal"),
    (rot.ENERGY_SOCIAL, "cockpit.energy_social"),
]


class DashboardWidget(QWidget):
    """Der Startbildschirm."""

    navigate_to = Signal(str)
    open_contact = Signal(int)

    def __init__(self, expert: bool = False, parent=None):
        super().__init__(parent)
        self._expert = expert
        self._excluded: set[int] = set()
        self._cards: list[NextStepCard] = []
        self._setup_ui()
        AppEventBus.instance().focus_changed.connect(self.refresh)
        self.refresh()

    # ── Aufbau ───────────────────────────────────────────────────────────────
    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        outer.addWidget(self._scroll)

        page = QWidget()
        self._scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 22)
        layout.setSpacing(14)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel(t("cockpit.title"))
        title.setObjectName("pageTitle")
        self._hint = QLabel("")
        self._hint.setObjectName("pageHint")
        titles.addWidget(title)
        titles.addWidget(self._hint)
        header.addLayout(titles)
        header.addStretch(1)
        header.addLayout(self._build_energy_chips())
        layout.addLayout(header)

        self._tiles_grid = QGridLayout()
        self._tiles_grid.setSpacing(12)
        self._tiles = [
            FocusTile(key, t(label_key),
                      theme.planned_accent() if urgency == "planned"
                      else theme.urgency_accent(urgency))
            for key, label_key, urgency in TILE_SPECS
        ]
        for tile in self._tiles:
            tile.double_clicked.connect(self._tile_opened)
            tile.clicked.connect(self._tile_opened)
        layout.addLayout(self._tiles_grid)

        self._capacity_label = QLabel("")
        self._capacity_label.setObjectName("pageHint")
        self._capacity_label.setWordWrap(True)
        layout.addWidget(self._capacity_label)

        steps_head = QHBoxLayout()
        steps_title = QLabel(t("cockpit.next_steps"))
        steps_title.setObjectName("pageTitle")
        steps_title.setStyleSheet("font-size: 16px;")
        self._reroll_button = QPushButton(t("cockpit.reroll"))
        self._reroll_button.setStyleSheet(theme.btn_quiet())
        self._reroll_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reroll_button.clicked.connect(self._reroll)
        steps_head.addWidget(steps_title)
        steps_head.addStretch(1)
        steps_head.addWidget(self._reroll_button)
        layout.addLayout(steps_head)

        self._steps_box = QVBoxLayout()
        self._steps_box.setSpacing(10)
        layout.addLayout(self._steps_box)

        self._planned_group = QGroupBox(t("cockpit.planned"))
        self._planned_layout = QVBoxLayout(self._planned_group)
        self._planned_layout.setContentsMargins(14, 8, 14, 12)
        layout.addWidget(self._planned_group)

        self._birthday_group = QGroupBox(t("cockpit.birthdays"))
        self._birthday_layout = QVBoxLayout(self._birthday_group)
        self._birthday_layout.setContentsMargins(14, 8, 14, 12)
        layout.addWidget(self._birthday_group)

        layout.addStretch(1)

    def _build_energy_chips(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        caption = QLabel(t("cockpit.energy_prompt"))
        caption.setObjectName("pageHint")
        row.addWidget(caption)
        self._energy_group = QButtonGroup(self)
        self._energy_group.setExclusive(True)
        for value, label_key in ENERGY_SPECS:
            button = QPushButton(t(label_key))
            button.setObjectName("energyButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setProperty("energy", value)
            self._energy_group.addButton(button)
            row.addWidget(button)
        self._energy_group.buttonClicked.connect(self._energy_chosen)
        return row

    # ── Daten ────────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        with db.get_session() as session:
            energy = dash.current_energy(session)
            cockpit = dash.build_cockpit(session, energy=energy,
                                         exclude_ids=self._excluded or None)
            if db.get_bool_setting(session, "bridge.enabled", True):
                bridge.publish_focus(cockpit)
        self._render(cockpit)

    def _render(self, cockpit: dash.Cockpit) -> None:
        summary = cockpit.summary
        for button in self._energy_group.buttons():
            button.setChecked(button.property("energy") == summary.energy)

        values = {"due_now": summary.due_now, "this_week": summary.this_week,
                  "planned": summary.planned, "all_good": summary.all_good}
        details = {"due_now": t("cockpit.tile_due_detail"),
                   "this_week": t("cockpit.tile_week_detail"),
                   "planned": t("cockpit.tile_planned_detail"),
                   "all_good": t("cockpit.tile_good_detail", count=summary.resting)}
        for tile in self._tiles:
            tile.set_value(values.get(tile.key, 0), details.get(tile.key, ""))

        self._hint.setText(t(cockpit.message) if cockpit.message else "")
        notes = summary.capacity_notes
        self._capacity_label.setText(
            t("common.hint", text=" \N{MIDDLE DOT} ".join(notes)) if notes else "")
        self._capacity_label.setVisible(bool(notes))

        self._clear_layout(self._steps_box)
        self._cards.clear()
        if cockpit.next_steps:
            for candidate in cockpit.next_steps:
                card = NextStepCard(candidate, expert=self._expert)
                card.done.connect(self._log_done)
                card.plan.connect(self._plan)
                card.snooze.connect(self._snooze)
                card.wish.connect(self._wish)
                card.opened.connect(self.open_contact.emit)
                self._steps_box.addWidget(card)
                self._cards.append(card)
        else:
            key = dash.CALM_MESSAGE if summary.is_calm else "cockpit.all_done"
            self._steps_box.addWidget(CalmCard(t(key)))
        self._reroll_button.setVisible(bool(cockpit.next_steps))

        self._clear_layout(self._planned_layout)
        # FPM-Prinzip: leere Bereiche verschwinden ganz.
        self._planned_group.setVisible(bool(cockpit.upcoming))
        for plan in cockpit.upcoming:
            label = QLabel(f"\N{BULLET}  {plan.label()}")
            label.setStyleSheet("border:none;")
            self._planned_layout.addWidget(label)

        self._clear_layout(self._birthday_layout)
        self._birthday_group.setVisible(bool(cockpit.birthdays))
        for birthday in cockpit.birthdays:
            label = QLabel(f"\N{BIRTHDAY CAKE}  {birthday.label()}")
            # Der Geburtstag von heute wird hervorgehoben, der Rest bleibt ruhig.
            label.setStyleSheet(f"border:none; color:{theme.color('erfolg')};"
                                if birthday.is_today else "border:none;")
            self._birthday_layout.addWidget(label)

        self._sync_responsive_layout()

    # ── Aktionen ─────────────────────────────────────────────────────────────
    def _log_done(self, contact_id: int, kind: str) -> None:
        """Schnellaktion: ein Klick, keine Rueckfrage, kein Dialog."""
        with db.get_session() as session:
            cs.log_interaction(session, contact_id, kind)
        bridge.emit_event(bridge.EVENT_INTERACTION_LOGGED,
                          {"contact_id": contact_id, "kind": kind})
        self._excluded.discard(contact_id)
        AppEventBus.instance().emit_interactions()

    def _plan(self, contact_id: int) -> None:
        with db.get_session() as session:
            people = [(c.id, c.name) for c in session.query(Contact).order_by(Contact.name)]
        dialog = PlanActivityDialog(people, {contact_id}, self)
        if dialog.exec() != PlanActivityDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not values["contact_ids"]:
            values["contact_ids"] = [contact_id]
        with db.get_session() as session:
            activity = cs.plan_activity(session, values["title"], values["planned_date"],
                                        values["contact_ids"], kind=values["kind"],
                                        start_time=values["start_time"])
            activity_id = activity.id
        bridge.emit_event(bridge.EVENT_PLAN_CREATED,
                          {"activity_id": activity_id, "date": values["planned_date"].isoformat()})
        AppEventBus.instance().emit_activities()

    def _snooze(self, contact_id: int, days: int) -> None:
        with db.get_session() as session:
            rot.snooze_contact(session, contact_id, days=days)
        AppEventBus.instance().emit_contacts()

    def _wish(self, contact_id: int) -> None:
        with db.get_session() as session:
            cs.set_wish(session, contact_id, boost=15)
        self._excluded.discard(contact_id)
        AppEventBus.instance().emit_contacts()

    def _reroll(self) -> None:
        """Andere Vorschlaege - dieselben Personen kommen nicht sofort wieder."""
        self._excluded |= {card.candidate.contact_id for card in self._cards}
        self.refresh()
        if not self._cards:          # Pool erschoepft: von vorne beginnen
            self._excluded.clear()
            self.refresh()

    def _energy_chosen(self, button) -> None:
        with db.get_session() as session:
            dash.set_energy(session, button.property("energy"))
        self._excluded.clear()
        self.refresh()

    def _tile_opened(self, key: str) -> None:
        self.navigate_to.emit("contacts")

    def set_expert(self, expert: bool) -> None:
        self._expert = bool(expert)
        self.refresh()

    # ── Layout ───────────────────────────────────────────────────────────────
    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _apply_responsive_layout(self, width: int) -> None:
        # Vier Kacheln sollen auf einem normalen Fenster in einer Reihe stehen.
        columns = 1 if width < 520 else (2 if width < 900 else 4)
        while self._tiles_grid.count():
            self._tiles_grid.takeAt(0)
        for index, tile in enumerate(self._tiles):
            self._tiles_grid.addWidget(tile, index // columns, index % columns)
        for column in range(columns):
            self._tiles_grid.setColumnStretch(column, 1)

    def _sync_responsive_layout(self) -> None:
        width = self._scroll.viewport().width() if hasattr(self, "_scroll") else self.width()
        self._apply_responsive_layout(max(320, width - 44))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_responsive_layout()
        # Die Viewport-Breite steht erst nach dem ersten Layoutdurchlauf fest.
        QTimer.singleShot(0, self._sync_responsive_layout)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_responsive_layout)
