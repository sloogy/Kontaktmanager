"""Kontaktliste mit Rotationszustand.

Die Liste zeigt bewusst dieselbe Sprache wie das Cockpit: Ampel und
Klartext-Status statt Punktzahlen. Der einzige Ort mit Zahlen ist der
Expertenmodus.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from freizeitmanager.database import db
from freizeitmanager.database.models import STATUS_ARCHIVED, Contact, Group, RelationshipLevel
from freizeitmanager.i18n.translator import t
from freizeitmanager.integration import lifeplanner_bridge as bridge
from freizeitmanager.logic import contact_service as cs
from freizeitmanager.logic import rotation_engine as rot
from freizeitmanager.logic.event_bus import AppEventBus
from freizeitmanager.ui import theme
from freizeitmanager.ui.dialogs import ContactDialog, LogInteractionDialog

COLUMN_KEYS = ["", "contacts.col_name", "contacts.col_level", "contacts.col_importance",
               "contacts.col_rhythm", "contacts.col_last", "contacts.col_status"]


class ContactsWidget(QWidget):
    """Alle Menschen, mit ihrem aktuellen Rotationszustand."""

    def __init__(self, expert: bool = False, parent=None):
        super().__init__(parent)
        self._expert = expert
        self._rows: list[int] = []
        self._setup_ui()
        bus = AppEventBus.instance()
        bus.contacts_changed.connect(self.refresh)
        bus.interactions_changed.connect(self.refresh)
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 22)
        layout.setSpacing(12)

        title = QLabel(t("contacts.title"))
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("common.search"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self.refresh)
        bar.addWidget(self._search, 1)

        add = QPushButton(t("contacts.new"))
        add.setStyleSheet(theme.btn_primary())
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.clicked.connect(self._create)
        bar.addWidget(add)

        self._log_button = QPushButton(t("contacts.log"))
        self._log_button.setStyleSheet(theme.btn_success())
        self._log_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._log_button.clicked.connect(self._log_selected)
        bar.addWidget(self._log_button)

        self._import_button = QPushButton(t("contacts.import"))
        self._import_button.setStyleSheet(theme.btn_secondary())
        self._import_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._import_button.setToolTip(t("import.tooltip"))
        self._import_button.clicked.connect(self._import_contacts)
        bar.addWidget(self._import_button)
        layout.addLayout(bar)

        self._table = QTableWidget(0, len(COLUMN_KEYS))
        self._table.setHorizontalHeaderLabels([t(key) if key else "" for key in COLUMN_KEYS])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(lambda: self._edit_selected())
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._context_menu)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in range(2, len(COLUMN_KEYS)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table, 1)

        self._empty = QLabel(t("contacts.empty"))
        self._empty.setObjectName("pageHint")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty)

    # ── Daten ────────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        needle = self._search.text().strip().lower()
        with db.get_session() as session:
            candidates = {c.contact_id: c for c in rot.evaluate_all(session)}
            contacts = session.query(Contact).order_by(Contact.name).all()
            rows = []
            for contact in contacts:
                if needle and needle not in contact.name.lower():
                    continue
                cand = candidates.get(contact.id)
                rows.append((
                    contact.id,
                    cand.icon if cand else "",
                    theme.urgency_accent(cand.urgency) if cand else None,
                    contact.name,
                    contact.level.name if contact.level else t("common.none"),
                    t(f"importance.short_{contact.importance}"),
                    t("contacts.rhythm_value", days=contact.target_interval_days),
                    cand.gap_text if cand else t("common.none"),
                    self._status_text(cand, contact),
                ))

        self._table.setRowCount(len(rows))
        self._rows = [r[0] for r in rows]
        for index, row in enumerate(rows):
            accent = row[2]
            for column, value in enumerate(row[1:2] + row[3:]):
                item = QTableWidgetItem(str(value))
                if column in (0, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 0 and accent:
                    # Der Ampelpunkt traegt dieselbe Farbe wie im Cockpit.
                    item.setForeground(QColor(accent))
                self._table.setItem(index, column, item)
        self._table.setVisible(bool(rows))
        self._empty.setVisible(not rows)
        self._empty.setText(t("contacts.no_match") if needle and not rows else t("contacts.empty"))

    @staticmethod
    def _status_text(cand, contact) -> str:
        from freizeitmanager.i18n.translator import format_short_date
        if cand is None:
            return t("common.none")
        if cand.planned_on is not None:
            return t("reason.planned_on", date=format_short_date(cand.planned_on))
        if cand.blocks:
            reasons = cand.why()
            return reasons[0] if reasons else t("rotation.resting")
        return cand.urgency_text

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._rows):
            return None
        return self._rows[row]

    # ── Aktionen ─────────────────────────────────────────────────────────────
    def _lists(self, session) -> tuple[list[str], list[str]]:
        levels = [row.name for row in
                  session.query(RelationshipLevel).order_by(RelationshipLevel.sort_order)]
        groups = [row.name for row in
                  session.query(Group).order_by(Group.sort_order, Group.name)]
        return levels, groups

    def _create(self) -> None:
        with db.get_session() as session:
            levels, groups = self._lists(session)
        dialog = ContactDialog(levels, groups, parent=self)
        if dialog.exec() != ContactDialog.DialogCode.Accepted:
            return
        with db.get_session() as session:
            cs.create_contact(session, **dialog.values())
        AppEventBus.instance().emit_contacts()

    def _edit_selected(self) -> None:
        contact_id = self._selected_id()
        if contact_id is None:
            return
        with db.get_session() as session:
            contact = session.get(Contact, contact_id)
            levels, groups = self._lists(session)
            dialog = ContactDialog(levels, groups, contact=contact, parent=self)
        if dialog.exec() != ContactDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        with db.get_session() as session:
            contact = session.get(Contact, contact_id)
            contact.name = values["name"]
            contact.importance = values["importance"]
            contact.target_interval_days = values["target_interval_days"]
            contact.interval_flex_days = values["interval_flex_days"]
            contact.status = values["status"]
            contact.notes = values["notes"]
            contact.birthday = values["birthday"]
            contact.birthday_has_year = values["birthday_has_year"]
            for attr in ("wants_meeting", "wants_call", "wants_message",
                         "prefers_weekday", "prefers_weekend"):
                setattr(contact, attr, values[attr])
            level = session.query(RelationshipLevel).filter_by(name=values["level"]).first() \
                if values["level"] else None
            contact.relationship_level_id = level.id if level else None
            contact.groups = [g for g in session.query(Group)
                              .filter(Group.name.in_(values["groups"] or [""]))]
            contact.tags.clear()
            session.flush()
            for tag_name in values["tags"]:
                tag = cs._get_or_create(session, cs.Tag, tag_name)
                if tag is not None:
                    contact.tags.append(tag)
        AppEventBus.instance().emit_contacts()

    def _import_contacts(self) -> None:
        """Liste aus CSV oder Excel einlesen. Der Dialog schreibt selbst."""
        from freizeitmanager.ui.import_dialog import run_import
        run_import(self, db.get_session,
                   on_done=lambda _result: AppEventBus.instance().emit_contacts())

    def _log_selected(self, kind: str | None = None) -> None:
        contact_id = self._selected_id()
        if contact_id is None:
            QMessageBox.information(self, t("contacts.log"), t("contacts.select_first"))
            return
        with db.get_session() as session:
            name = session.get(Contact, contact_id).name
        dialog = LogInteractionDialog(name, kind or "meet", self)
        if dialog.exec() != LogInteractionDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        with db.get_session() as session:
            cs.log_interaction(session, contact_id, **values)
        bridge.emit_event(bridge.EVENT_INTERACTION_LOGGED,
                          {"contact_id": contact_id, "kind": values["kind"]})
        AppEventBus.instance().emit_interactions()

    def _context_menu(self, pos) -> None:
        contact_id = self._selected_id()
        if contact_id is None:
            return
        menu = QMenu(self)
        act_log = menu.addAction(t("contacts.menu_log"))
        act_edit = menu.addAction(t("contacts.menu_edit"))
        menu.addSeparator()
        act_wish = menu.addAction(t("contacts.menu_wish"))
        act_snooze = menu.addAction(t("contacts.menu_snooze"))
        menu.addSeparator()
        act_archive = menu.addAction(t("contacts.menu_archive"))

        chosen = menu.exec(self._table.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is act_log:
            self._log_selected()
        elif chosen is act_edit:
            self._edit_selected()
        elif chosen is act_wish:
            with db.get_session() as session:
                cs.set_wish(session, contact_id, boost=15)
            AppEventBus.instance().emit_contacts()
        elif chosen is act_snooze:
            with db.get_session() as session:
                rot.snooze_contact(session, contact_id, days=30, reason="manual")
            AppEventBus.instance().emit_contacts()
        elif chosen is act_archive:
            with db.get_session() as session:
                session.get(Contact, contact_id).status = STATUS_ARCHIVED
            AppEventBus.instance().emit_contacts()

    def select_contact(self, contact_id: int) -> None:
        if contact_id in self._rows:
            self._table.selectRow(self._rows.index(contact_id))

    def set_expert(self, expert: bool) -> None:
        self._expert = bool(expert)
        self.refresh()
