"""Dialoge: Kontakt anlegen/bearbeiten, Termin planen, Kontakt nachtragen."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from freizeitmanager.database.models import (
    KIND_CALL,
    KIND_CALL_LONG,
    KIND_CHAT,
    KIND_MEET,
    KIND_MEET_LONG,
    KIND_MESSAGE,
    KIND_REACTION,
    QUALITY_INTENSE,
    QUALITY_NORMAL,
    QUALITY_SHORT,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    STATUS_LOW,
    STATUS_NO_ROTATION,
    STATUS_PAUSED,
)
from freizeitmanager.i18n.translator import t
from freizeitmanager.logic.contact_import import YEAR_UNKNOWN

# Auswahllisten werden ueber Schluessel gefuehrt und erst beim Aufbau des
# Dialogs uebersetzt - so wirkt ein Sprachwechsel sofort.
KIND_ORDER = (KIND_MEET, KIND_MEET_LONG, KIND_CALL, KIND_CALL_LONG,
              KIND_CHAT, KIND_MESSAGE, KIND_REACTION)
QUALITY_ORDER = (QUALITY_SHORT, QUALITY_NORMAL, QUALITY_INTENSE)
STATUS_ORDER = (STATUS_ACTIVE, STATUS_LOW, STATUS_NO_ROTATION, STATUS_PAUSED, STATUS_ARCHIVED)
IMPORTANCE_ORDER = (5, 4, 3, 2, 1)

# Ein QDateEdit kennt keinen leeren Zustand. Das Minimaldatum dient deshalb als
# "kein Geburtstag hinterlegt" und wird ueber setSpecialValueText beschriftet.
NO_BIRTHDAY = QDate(1800, 1, 1)


def kind_choices(limit: int | None = None) -> list[tuple[str, str]]:
    values = KIND_ORDER[:limit] if limit else KIND_ORDER
    return [(value, t(f"interaction.{value}")) for value in values]


def quality_choices() -> list[tuple[str, str]]:
    return [(value, t(f"interaction.quality_{value}")) for value in QUALITY_ORDER]


def status_choices() -> list[tuple[str, str]]:
    return [(value, t(f"status.{value}")) for value in STATUS_ORDER]


def importance_choices() -> list[tuple[int, str]]:
    return [(value, t(f"importance.{value}")) for value in IMPORTANCE_ORDER]


def _fill(combo: QComboBox, pairs, current=None) -> None:
    for value, label in pairs:
        combo.addItem(label, value)
    if current is not None:
        index = combo.findData(current)
        if index >= 0:
            combo.setCurrentIndex(index)


class LogInteractionDialog(QDialog):
    """Kontakt nachtragen. Nur fuer den Fall, dass die Schnellaktion nicht passt."""

    def __init__(self, contact_name: str, kind: str = KIND_MEET, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("interaction.title", name=contact_name))
        self.setMinimumWidth(400)
        form = QFormLayout(self)

        self.kind = QComboBox()
        _fill(self.kind, kind_choices(), kind)
        self.when = QDateEdit(QDate.currentDate())
        self.when.setCalendarPopup(True)
        self.when.setDisplayFormat("dd.MM.yyyy")
        self.when.setMaximumDate(QDate.currentDate())
        self.quality = QComboBox()
        _fill(self.quality, quality_choices(), QUALITY_NORMAL)
        self.duration = QSpinBox()
        self.duration.setRange(0, 1440)
        self.duration.setSingleStep(15)
        self.duration.setSuffix(t("interaction.duration_suffix"))
        self.duration.setSpecialValueText(t("interaction.duration_none"))
        self.note = QLineEdit()
        self.note.setPlaceholderText(t("common.optional"))

        form.addRow(t("interaction.kind"), self.kind)
        form.addRow(t("interaction.when"), self.when)
        form.addRow(t("interaction.quality"), self.quality)
        form.addRow(t("interaction.duration"), self.duration)
        form.addRow(t("interaction.note"), self.note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> dict:
        return {
            "kind": self.kind.currentData(),
            "occurred_on": self.when.date().toPython(),
            "quality": self.quality.currentData(),
            "duration_min": self.duration.value() or None,
            "note": self.note.text().strip() or None,
        }


class PlanActivityDialog(QDialog):
    """Termin planen. Nimmt die Person aus dem Vorschlag bereits mit."""

    def __init__(self, contacts: list[tuple[int, str]], preselect: set[int] | None = None,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("activity.title"))
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title = QLineEdit(t("activity.default_title"))
        self.when = QDateEdit(QDate.currentDate().addDays(3))
        self.when.setCalendarPopup(True)
        self.when.setDisplayFormat("dd.MM.yyyy")
        self.when.setMinimumDate(QDate.currentDate())
        self.start = QLineEdit()
        self.start.setPlaceholderText(t("activity.time_placeholder"))
        self.kind = QComboBox()
        _fill(self.kind, kind_choices(limit=4), KIND_MEET)
        form.addRow(t("activity.name"), self.title)
        form.addRow(t("activity.date"), self.when)
        form.addRow(t("activity.time"), self.start)
        form.addRow(t("activity.kind"), self.kind)
        layout.addLayout(form)

        layout.addWidget(QLabel(t("activity.participants")))
        self.people = QListWidget()
        self.people.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.people.setMaximumHeight(180)
        for cid, name in contacts:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, cid)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if preselect and cid in preselect
                               else Qt.CheckState.Unchecked)
            self.people.addItem(item)
        layout.addWidget(self.people)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        chosen = []
        for row in range(self.people.count()):
            item = self.people.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                chosen.append(int(item.data(Qt.ItemDataRole.UserRole)))
        raw_time = self.start.text().strip()
        return {
            "title": self.title.text().strip() or t("activity.default_title"),
            "planned_date": self.when.date().toPython(),
            "kind": self.kind.currentData(),
            "start_time": raw_time or None,
            "contact_ids": chosen,
        }


class ContactDialog(QDialog):
    """Kontakt anlegen oder bearbeiten.

    Wichtigkeit und gewuenschter Rhythmus stehen bewusst nebeneinander -
    der Zusammenhang soll sichtbar sein, ohne dass eines das andere bestimmt.
    """

    def __init__(self, levels: list[str], groups: list[str],
                 contact=None, tags: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("contact.edit_title") if contact else t("contact.new_title"))
        self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit(contact.name if contact else "")
        self.level = QComboBox()
        self.level.addItem(t("common.none"), None)
        for name in levels:
            self.level.addItem(name, name)
        if contact is not None and contact.level is not None:
            index = self.level.findData(contact.level.name)
            if index >= 0:
                self.level.setCurrentIndex(index)

        self.importance = QComboBox()
        _fill(self.importance, importance_choices(), contact.importance if contact else 3)

        self.interval = QSpinBox()
        self.interval.setRange(1, 730)
        self.interval.setSuffix(t("contact.interval_suffix"))
        self.interval.setValue(contact.target_interval_days if contact else 30)
        self.flex = QSpinBox()
        self.flex.setRange(0, 180)
        self.flex.setSuffix(t("contact.interval_suffix"))
        self.flex.setValue(contact.interval_flex_days if contact else 7)

        self.status = QComboBox()
        _fill(self.status, status_choices(), contact.status if contact else STATUS_ACTIVE)

        self.birthday = QDateEdit()
        self.birthday.setCalendarPopup(True)
        self.birthday.setMinimumDate(NO_BIRTHDAY)
        self.birthday.setMaximumDate(QDate.currentDate())
        self.birthday.setSpecialValueText(t("contact.birthday_none"))
        self.no_year = QCheckBox(t("contact.birthday_no_year"))
        self.no_year.toggled.connect(self._apply_birthday_format)

        existing = getattr(contact, "birthday", None) if contact else None
        if existing is not None:
            self.birthday.setDate(QDate(existing.year, existing.month, existing.day))
            self.no_year.setChecked(not contact.birthday_has_year)
        else:
            self.birthday.setDate(NO_BIRTHDAY)
        self._apply_birthday_format(self.no_year.isChecked())

        birthday_row = QHBoxLayout()
        birthday_row.setContentsMargins(0, 0, 0, 0)
        birthday_row.addWidget(self.birthday, 1)
        birthday_row.addWidget(self.no_year)

        form.addRow(t("contact.name"), self.name)
        form.addRow(t("contact.level"), self.level)
        form.addRow(t("contact.importance"), self.importance)
        form.addRow(t("contact.interval"), self.interval)
        form.addRow(t("contact.flex"), self.flex)
        form.addRow(t("contact.status"), self.status)
        form.addRow(t("contact.birthday"), birthday_row)
        layout.addLayout(form)

        channels = QGroupBox(t("contact.channels"))
        row = QHBoxLayout(channels)
        self.wants_meeting = QCheckBox(t("contact.wants_meeting"))
        self.wants_call = QCheckBox(t("contact.wants_call"))
        self.wants_message = QCheckBox(t("contact.wants_message"))
        for box, attr in ((self.wants_meeting, "wants_meeting"),
                          (self.wants_call, "wants_call"),
                          (self.wants_message, "wants_message")):
            box.setChecked(getattr(contact, attr) if contact else True)
            row.addWidget(box)
        layout.addWidget(channels)

        timing = QGroupBox(t("contact.timing"))
        trow = QHBoxLayout(timing)
        self.prefers_weekday = QCheckBox(t("contact.weekday"))
        self.prefers_weekend = QCheckBox(t("contact.weekend"))
        for box, attr in ((self.prefers_weekday, "prefers_weekday"),
                          (self.prefers_weekend, "prefers_weekend")):
            box.setChecked(getattr(contact, attr) if contact else True)
            trow.addWidget(box)
        layout.addWidget(timing)

        self.groups = QListWidget()
        self.groups.setMaximumHeight(110)
        current_groups = {g.name for g in contact.groups} if contact else set()
        for name in groups:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in current_groups
                               else Qt.CheckState.Unchecked)
            self.groups.addItem(item)
        layout.addWidget(QLabel(t("contact.groups")))
        layout.addWidget(self.groups)

        self.tags = QLineEdit(", ".join(t.name for t in contact.tags) if contact else "")
        self.tags.setPlaceholderText(t("contact.tags_placeholder"))
        layout.addWidget(QLabel(t("contact.tags")))
        layout.addWidget(self.tags)

        self.notes = QTextEdit(contact.notes or "" if contact else "")
        self.notes.setMaximumHeight(80)
        layout.addWidget(QLabel(t("contact.notes")))
        layout.addWidget(self.notes)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_birthday_format(self, no_year: bool) -> None:
        """Ohne Jahrgang wird das Jahr auch nicht angezeigt.

        Gespeichert wird es trotzdem - als YEAR_UNKNOWN, damit Tag und Monat
        nicht verloren gehen.
        """
        self.birthday.setDisplayFormat("dd.MM." if no_year else "dd.MM.yyyy")

    def birthday_values(self) -> tuple[object, bool]:
        """Geburtstag und ob der Jahrgang echt ist. Ohne Angabe: (None, True)."""
        chosen = self.birthday.date()
        if chosen <= NO_BIRTHDAY:
            return None, True
        if self.no_year.isChecked():
            return date(YEAR_UNKNOWN, chosen.month(), chosen.day()), False
        return chosen.toPython(), True

    def _accept_if_valid(self) -> None:
        if not self.name.text().strip():
            self.name.setFocus()
            from freizeitmanager.ui import theme
            self.name.setStyleSheet(f"border: 1px solid {theme.color('gefahr')};")
            return
        self.accept()

    def values(self) -> dict:
        checked_groups = [self.groups.item(i).text() for i in range(self.groups.count())
                          if self.groups.item(i).checkState() == Qt.CheckState.Checked]
        birthday, has_year = self.birthday_values()
        return {
            "name": self.name.text().strip(),
            "birthday": birthday,
            "birthday_has_year": has_year,
            "level": self.level.currentData(),
            "importance": int(self.importance.currentData()),
            "target_interval_days": self.interval.value(),
            "interval_flex_days": self.flex.value(),
            "status": self.status.currentData(),
            "wants_meeting": self.wants_meeting.isChecked(),
            "wants_call": self.wants_call.isChecked(),
            "wants_message": self.wants_message.isChecked(),
            "prefers_weekday": self.prefers_weekday.isChecked(),
            "prefers_weekend": self.prefers_weekend.isChecked(),
            "groups": checked_groups,
            "tags": [t.strip() for t in self.tags.text().split(",") if t.strip()],
            "notes": self.notes.toPlainText().strip() or None,
        }
