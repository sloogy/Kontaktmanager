"""Einstellungen: Kapazitaet, Fokus, LifePlanner.

Die Kapazitaetsgrenzen sind die weiterentwickelten Felder des alten
Kontaktmanagers. Neu ist, dass sie tatsaechlich wirken.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
from freizeitmanager.i18n.translator import LANGUAGES, current_language, set_language, t
from freizeitmanager.logic.event_bus import AppEventBus
from freizeitmanager.ui import theme


def _translator():
    from freizeitmanager.i18n.translator import Translator
    return Translator.instance()


def _weekday_short(index: int) -> str:
    """Kurzname des Wochentags in der aktiven Sprache."""
    from datetime import date, timedelta
    # 2026-08-17 ist ein Montag - ergibt Index 0.
    return _translator().weekday_name(date(2026, 8, 17) + timedelta(days=index))


class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 22)
        layout.setSpacing(12)

        title = QLabel(t("settings.title"))
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Die Sprache steht bewusst ganz oben: Wer sie sucht, versteht den Rest
        # der Seite moeglicherweise noch nicht.
        language_group = QGroupBox(t("settings.language_group"))
        language_form = QFormLayout(language_group)
        self.language = QComboBox()
        for code, name in LANGUAGES.items():
            self.language.addItem(name, code)
        index = self.language.findData(current_language())
        if index >= 0:
            self.language.setCurrentIndex(index)
        self.language.currentIndexChanged.connect(self._language_chosen)
        language_form.addRow(t("settings.language"), self.language)
        hint = QLabel(t("settings.language_hint"))
        hint.setObjectName("pageHint")
        language_form.addRow(hint)
        layout.addWidget(language_group)

        capacity = QGroupBox(t("settings.capacity"))
        form = QFormLayout(capacity)
        self.week_active = QCheckBox(t("settings.limit"))
        self.week_days = QSpinBox()
        self.week_days.setRange(1, 7)
        self.week_days.setSuffix(t("settings.days_suffix"))
        form.addRow(self._pair(t("settings.days_per_week"), self.week_active, self.week_days))

        self.weekend_active = QCheckBox(t("settings.limit"))
        self.weekends = QSpinBox()
        self.weekends.setRange(1, 5)
        form.addRow(self._pair(t("settings.weekends_per_month"), self.weekend_active, self.weekends))

        self.cooldown = QSpinBox()
        self.cooldown.setRange(0, 30)
        self.cooldown.setSuffix(t("settings.days_suffix"))
        self.cooldown.setToolTip(t("settings.cooldown_tooltip"))
        form.addRow(t("settings.cooldown"), self.cooldown)

        self.weekday_active = QCheckBox(t("settings.weekdays_only"))
        form.addRow(self.weekday_active)
        days_row = QHBoxLayout()
        self.weekday_boxes = []
        for index in range(7):
            box = QCheckBox(_weekday_short(index))
            box.setProperty("weekday", index)
            self.weekday_boxes.append(box)
            days_row.addWidget(box)
        days_row.addStretch(1)
        form.addRow(days_row)
        layout.addWidget(capacity)

        focus = QGroupBox(t("settings.focus"))
        focus_form = QFormLayout(focus)
        self.max_suggestions = QSpinBox()
        self.max_suggestions.setRange(1, 6)
        self.max_suggestions.setToolTip(t("settings.max_suggestions_tooltip"))
        focus_form.addRow(t("settings.max_suggestions"), self.max_suggestions)
        layout.addWidget(focus)

        host = QGroupBox(t("settings.lifeplanner"))
        host_form = QFormLayout(host)
        self.bridge_enabled = QCheckBox(t("settings.bridge_enabled"))
        self.bridge_enabled.setToolTip(t("settings.bridge_tooltip"))
        host_form.addRow(self.bridge_enabled)
        state = t("settings.mode_hosted") if paths.is_hosted() else t("settings.mode_standalone")
        host_form.addRow(t("settings.mode"), QLabel(state))
        host_form.addRow(t("settings.data_dir"), QLabel(str(paths.data_dir())))
        layout.addWidget(host)

        row = QHBoxLayout()
        save = QPushButton(t("common.save"))
        save.setStyleSheet(theme.BTN_PRIMARY)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._save)
        backup = QPushButton(t("settings.backup"))
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
        self._status.setText(t("settings.saved"))
        AppEventBus.instance().emit_all()

    def _language_chosen(self) -> None:
        """Sprache sofort umschalten und speichern.

        Ein Neustart waere hier eine unnoetige Huerde: Der Nutzer sieht
        gerade diese Seite und will das Ergebnis sehen.
        """
        code = self.language.currentData()
        set_language(code)
        with db.get_session() as session:
            db.set_setting(session, "ui.language", code)
        AppEventBus.instance().language_changed.emit()

    def _backup(self) -> None:
        target = db.create_backup()
        self._status.setText(t("settings.backup_done", path=target) if target
                             else t("settings.backup_none"))
