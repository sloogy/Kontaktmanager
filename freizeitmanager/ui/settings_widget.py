"""Einstellungen: Kapazitaet, Fokus, LifePlanner.

Die Kapazitaetsgrenzen sind die weiterentwickelten Felder des alten
Kontaktmanagers. Neu ist, dass sie tatsaechlich wirken.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from freizeitmanager import paths
from freizeitmanager.database import db
from freizeitmanager.logic.event_bus import AppEventBus
from freizeitmanager.ui import theme

WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 22)
        layout.setSpacing(12)

        title = QLabel("Einstellungen")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        capacity = QGroupBox("Soziale Kapazit\N{LATIN SMALL LETTER A WITH DIAERESIS}t")
        form = QFormLayout(capacity)
        self.week_active = QCheckBox("begrenzen")
        self.week_days = QSpinBox()
        self.week_days.setRange(1, 7)
        self.week_days.setSuffix(" Tage")
        form.addRow(self._pair("Soziale Tage pro Woche", self.week_active, self.week_days))

        self.weekend_active = QCheckBox("begrenzen")
        self.weekends = QSpinBox()
        self.weekends.setRange(1, 5)
        form.addRow(self._pair("Wochenenden pro Monat", self.weekend_active, self.weekends))

        self.cooldown = QSpinBox()
        self.cooldown.setRange(0, 30)
        self.cooldown.setSuffix(" Tage")
        self.cooldown.setToolTip("Nach einem richtigen Kontakt so lange keinen neuen "
                                 "Vorschlag. Nachrichten und Reaktionen zaehlen nicht.")
        form.addRow("Ruhe nach Kontakt", self.cooldown)

        self.weekday_active = QCheckBox("nur bestimmte Wochentage")
        form.addRow(self.weekday_active)
        days_row = QHBoxLayout()
        self.weekday_boxes = []
        for index, label in enumerate(WEEKDAYS):
            box = QCheckBox(label)
            box.setProperty("weekday", index)
            self.weekday_boxes.append(box)
            days_row.addWidget(box)
        days_row.addStretch(1)
        form.addRow(days_row)
        layout.addWidget(capacity)

        focus = QGroupBox("Fokus")
        focus_form = QFormLayout(focus)
        self.max_suggestions = QSpinBox()
        self.max_suggestions.setRange(1, 6)
        self.max_suggestions.setToolTip("Mehr als drei Vorschlaege auf einmal erzeugen "
                                        "erfahrungsgemaess Druck statt Klarheit.")
        focus_form.addRow("Vorschl\N{LATIN SMALL LETTER A WITH DIAERESIS}ge im Cockpit", self.max_suggestions)
        layout.addWidget(focus)

        host = QGroupBox("LifePlanner")
        host_form = QFormLayout(host)
        self.bridge_enabled = QCheckBox("Fokus an den LifePlanner melden")
        self.bridge_enabled.setToolTip("Es werden nur Zaehlwerte und die naechsten "
                                       "Schritte uebergeben - niemals Notizen.")
        host_form.addRow(self.bridge_enabled)
        state = "verbunden" if paths.is_hosted() else "eigenst\N{LATIN SMALL LETTER A WITH DIAERESIS}ndig"
        host_form.addRow("Betrieb", QLabel(state))
        host_form.addRow("Datenordner", QLabel(str(paths.data_dir())))
        layout.addWidget(host)

        row = QHBoxLayout()
        save = QPushButton("Speichern")
        save.setStyleSheet(theme.BTN_PRIMARY)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._save)
        backup = QPushButton("Sicherung anlegen")
        backup.setStyleSheet(theme.BTN_SECONDARY)
        backup.setCursor(Qt.CursorShape.PointingHandCursor)
        backup.clicked.connect(self._backup)
        row.addWidget(save)
        row.addWidget(backup)
        row.addStretch(1)
        layout.addLayout(row)
        self._status = QLabel("")
        self._status.setObjectName("pageHint")
        layout.addWidget(self._status)
        layout.addStretch(1)

        self.load()

    @staticmethod
    def _pair(label: str, check: QCheckBox, spin: QSpinBox) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(check)
        row.addWidget(spin)
        row.addStretch(1)
        return row

    def load(self) -> None:
        with db.get_session() as session:
            self.week_active.setChecked(db.get_bool_setting(session, "capacity.max_social_days_per_week_active", True))
            self.week_days.setValue(db.get_int_setting(session, "capacity.max_social_days_per_week", 3))
            self.weekend_active.setChecked(db.get_bool_setting(session, "capacity.max_weekends_per_month_active", True))
            self.weekends.setValue(db.get_int_setting(session, "capacity.max_weekends_per_month", 3))
            self.cooldown.setValue(db.get_int_setting(session, "capacity.min_days_between_contacts", 2))
            self.weekday_active.setChecked(db.get_bool_setting(session, "capacity.allowed_weekdays_active", False))
            allowed = {int(p) for p in db.get_setting(session, "capacity.allowed_weekdays", "0,1,2,3,4,5,6").split(",") if p.strip().isdigit()}
            for box in self.weekday_boxes:
                box.setChecked(int(box.property("weekday")) in allowed)
            self.max_suggestions.setValue(db.get_int_setting(session, "focus.max_suggestions", 3))
            self.bridge_enabled.setChecked(db.get_bool_setting(session, "bridge.enabled", True))

    def _save(self) -> None:
        allowed = ",".join(str(box.property("weekday")) for box in self.weekday_boxes if box.isChecked())
        with db.get_session() as session:
            db.set_setting(session, "capacity.max_social_days_per_week_active", "1" if self.week_active.isChecked() else "0")
            db.set_setting(session, "capacity.max_social_days_per_week", self.week_days.value())
            db.set_setting(session, "capacity.max_weekends_per_month_active", "1" if self.weekend_active.isChecked() else "0")
            db.set_setting(session, "capacity.max_weekends_per_month", self.weekends.value())
            db.set_setting(session, "capacity.min_days_between_contacts", self.cooldown.value())
            db.set_setting(session, "capacity.allowed_weekdays_active", "1" if self.weekday_active.isChecked() else "0")
            db.set_setting(session, "capacity.allowed_weekdays", allowed or "0,1,2,3,4,5,6")
            db.set_setting(session, "focus.max_suggestions", self.max_suggestions.value())
            db.set_setting(session, "bridge.enabled", "1" if self.bridge_enabled.isChecked() else "0")
        self._status.setText("Gespeichert.")
        AppEventBus.instance().emit_all()

    def _backup(self) -> None:
        target = db.create_backup()
        self._status.setText(f"Sicherung: {target}" if target else "Noch keine Datenbank vorhanden.")
