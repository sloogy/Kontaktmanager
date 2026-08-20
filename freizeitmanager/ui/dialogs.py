"""Dialoge: Kontakt anlegen/bearbeiten, Termin planen, Kontakt nachtragen."""
from __future__ import annotations

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

KIND_LABELS = [
    (KIND_MEET, "Treffen"),
    (KIND_MEET_LONG, "Langer gemeinsamer Tag"),
    (KIND_CALL, "Kurzes Telefonat"),
    (KIND_CALL_LONG, "Langes Gespr\N{LATIN SMALL LETTER A WITH DIAERESIS}ch / Video"),
    (KIND_CHAT, "L\N{LATIN SMALL LETTER A WITH DIAERESIS}ngerer Chat"),
    (KIND_MESSAGE, "Nachricht"),
    (KIND_REACTION, "Reaktion / Emoji"),
]

QUALITY_LABELS = [(QUALITY_SHORT, "kurz"), (QUALITY_NORMAL, "normal"), (QUALITY_INTENSE, "intensiv")]

STATUS_LABELS = [
    (STATUS_ACTIVE, "Aktiv"),
    (STATUS_LOW, "Gerade weniger Kontakt"),
    (STATUS_NO_ROTATION, "Nicht in der Rotation"),
    (STATUS_PAUSED, "Pausiert"),
    (STATUS_ARCHIVED, "Archiviert"),
]

IMPORTANCE_LABELS = [
    (5, "A \N{EN DASH} engster Mensch"),
    (4, "B \N{EN DASH} wichtiger Freund"),
    (3, "C \N{EN DASH} Freund"),
    (2, "D \N{EN DASH} Bekannter"),
    (1, "E \N{EN DASH} lose Bekanntschaft"),
]


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
        self.setWindowTitle(f"Kontakt eintragen \N{EN DASH} {contact_name}")
        self.setMinimumWidth(400)
        form = QFormLayout(self)

        self.kind = QComboBox()
        _fill(self.kind, KIND_LABELS, kind)
        self.when = QDateEdit(QDate.currentDate())
        self.when.setCalendarPopup(True)
        self.when.setDisplayFormat("dd.MM.yyyy")
        self.when.setMaximumDate(QDate.currentDate())
        self.quality = QComboBox()
        _fill(self.quality, QUALITY_LABELS, QUALITY_NORMAL)
        self.duration = QSpinBox()
        self.duration.setRange(0, 1440)
        self.duration.setSingleStep(15)
        self.duration.setSuffix(" min")
        self.duration.setSpecialValueText("nicht angeben")
        self.note = QLineEdit()
        self.note.setPlaceholderText("optional")

        form.addRow("Art", self.kind)
        form.addRow("Wann", self.when)
        form.addRow("Intensit\N{LATIN SMALL LETTER A WITH DIAERESIS}t", self.quality)
        form.addRow("Dauer", self.duration)
        form.addRow("Notiz", self.note)

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
        self.setWindowTitle("Treffen planen")
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title = QLineEdit("Treffen")
        self.when = QDateEdit(QDate.currentDate().addDays(3))
        self.when.setCalendarPopup(True)
        self.when.setDisplayFormat("dd.MM.yyyy")
        self.when.setMinimumDate(QDate.currentDate())
        self.start = QLineEdit()
        self.start.setPlaceholderText("z.B. 18:30 (optional)")
        self.kind = QComboBox()
        _fill(self.kind, KIND_LABELS[:4], KIND_MEET)
        form.addRow("Titel", self.title)
        form.addRow("Datum", self.when)
        form.addRow("Uhrzeit", self.start)
        form.addRow("Art", self.kind)
        layout.addLayout(form)

        layout.addWidget(QLabel("Wer ist dabei?"))
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
            "title": self.title.text().strip() or "Treffen",
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
        self.setWindowTitle("Kontakt bearbeiten" if contact else "Neuer Kontakt")
        self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit(contact.name if contact else "")
        self.level = QComboBox()
        self.level.addItem("\N{EM DASH}", None)
        for name in levels:
            self.level.addItem(name, name)
        if contact is not None and contact.level is not None:
            index = self.level.findData(contact.level.name)
            if index >= 0:
                self.level.setCurrentIndex(index)

        self.importance = QComboBox()
        _fill(self.importance, IMPORTANCE_LABELS, contact.importance if contact else 3)

        self.interval = QSpinBox()
        self.interval.setRange(1, 730)
        self.interval.setSuffix(" Tage")
        self.interval.setValue(contact.target_interval_days if contact else 30)
        self.flex = QSpinBox()
        self.flex.setRange(0, 180)
        self.flex.setSuffix(" Tage")
        self.flex.setValue(contact.interval_flex_days if contact else 7)

        self.status = QComboBox()
        _fill(self.status, STATUS_LABELS, contact.status if contact else STATUS_ACTIVE)

        form.addRow("Name", self.name)
        form.addRow("Beziehungsgrad", self.level)
        form.addRow("Wichtigkeit", self.importance)
        form.addRow("Kontakt alle", self.interval)
        form.addRow("Toleranz", self.flex)
        form.addRow("Status", self.status)
        layout.addLayout(form)

        channels = QGroupBox("Wie ist Kontakt willkommen?")
        row = QHBoxLayout(channels)
        self.wants_meeting = QCheckBox("Treffen")
        self.wants_call = QCheckBox("Telefon")
        self.wants_message = QCheckBox("Nachrichten")
        for box, attr in ((self.wants_meeting, "wants_meeting"),
                          (self.wants_call, "wants_call"),
                          (self.wants_message, "wants_message")):
            box.setChecked(getattr(contact, attr) if contact else True)
            row.addWidget(box)
        layout.addWidget(channels)

        timing = QGroupBox("Wann passt es meistens?")
        trow = QHBoxLayout(timing)
        self.prefers_weekday = QCheckBox("Werktags")
        self.prefers_weekend = QCheckBox("Wochenende")
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
        layout.addWidget(QLabel("Gruppen"))
        layout.addWidget(self.groups)

        self.tags = QLineEdit(", ".join(t.name for t in contact.tags) if contact else "")
        self.tags.setPlaceholderText("Brettspiele, Essen, spontan \N{EM DASH} durch Komma getrennt")
        layout.addWidget(QLabel("Tags"))
        layout.addWidget(self.tags)

        self.notes = QTextEdit(contact.notes or "" if contact else "")
        self.notes.setMaximumHeight(80)
        layout.addWidget(QLabel("Notizen"))
        layout.addWidget(self.notes)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_if_valid(self) -> None:
        if not self.name.text().strip():
            self.name.setFocus()
            self.name.setStyleSheet("border: 1px solid #dc2626;")
            return
        self.accept()

    def values(self) -> dict:
        checked_groups = [self.groups.item(i).text() for i in range(self.groups.count())
                          if self.groups.item(i).checkState() == Qt.CheckState.Checked]
        return {
            "name": self.name.text().strip(),
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
