"""Import einer Personenliste: Datei waehlen, Vorschau, dann erst schreiben.

Der Dialog haelt sich an die Trennung aus ``logic.contact_import``: bis der
Nutzer bestaetigt, ist nichts geschrieben. Jede Zeile traegt ihre eigene
Entscheidung, damit ein bestehender Kontakt nie ungefragt veraendert wird.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from freizeitmanager.i18n.translator import format_date, format_short_date, t
from freizeitmanager.logic import contact_import as imp
from freizeitmanager.ui import theme

COLUMN_KEYS = ("import.col_name", "import.col_birthday", "import.col_group",
               "import.col_state", "import.col_action")


def birthday_text(row: imp.ImportRow) -> str:
    """Ohne echten Jahrgang wird auch keiner angezeigt."""
    if row.birthday is None:
        return t("common.none")
    if not row.birthday_has_year:
        return format_short_date(row.birthday)
    return format_date(row.birthday)


def action_choices(row: imp.ImportRow) -> list[tuple[imp.RowAction, str]]:
    """Was fuer diese Zeile ueberhaupt zur Wahl steht.

    Fuer einen bestehenden Kontakt gibt es kein "anlegen", fuer einen neuen
    kein "ergaenzen" - eine Auswahl, die nichts tun kann, waere eine Falle.
    """
    if row.is_conflict:
        return [(imp.RowAction.SKIP, t("import.action_skip")),
                (imp.RowAction.FILL, t("import.action_fill"))]
    return [(imp.RowAction.CREATE, t("import.action_create")),
            (imp.RowAction.SKIP, t("import.action_skip"))]


def choose_file(parent: QWidget | None = None) -> Path | None:
    """Dateiauswahl mit den Endungen, die ``contact_import`` wirklich liest."""
    patterns = " ".join(sorted(f"*{s}" for s in imp.CSV_SUFFIXES | imp.EXCEL_SUFFIXES))
    chosen, _selected = QFileDialog.getOpenFileName(
        parent, t("import.choose_file"), "",
        f"{t('import.file_filter')} ({patterns})")
    return Path(chosen) if chosen else None


class ImportPreviewDialog(QDialog):
    """Zeigt, was der Import taete - und laesst jede Zeile einzeln entscheiden."""

    def __init__(self, preview: imp.ImportPreview, source: Path, parent=None):
        super().__init__(parent)
        self.preview = preview
        self.setWindowTitle(t("import.title"))
        self.setMinimumSize(760, 540)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        heading = QLabel(t("import.source", file=source.name))
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)

        summary = QLabel(t("import.summary",
                           new=len(preview.new_rows),
                           conflicts=len(preview.conflicts),
                           unusable=len(preview.unusable),
                           birthdays=preview.with_birthday))
        summary.setWordWrap(True)
        layout.addWidget(summary)

        detected = QLabel(t("import.detected", columns=self._detected_text()))
        detected.setObjectName("pageHint")
        detected.setWordWrap(True)
        layout.addWidget(detected)

        # Die anwendbaren Zeilen; unlesbare stehen nur in der Zusammenfassung,
        # weil es an ihnen nichts zu entscheiden gibt.
        self._rows = [row for row in preview.rows if row.is_usable]
        self._table = QTableWidget(len(self._rows), len(COLUMN_KEYS))
        self._table.setHorizontalHeaderLabels([t(key) for key in COLUMN_KEYS])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(COLUMN_KEYS)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)

        self._combos: list[QComboBox] = []
        for index, row in enumerate(self._rows):
            self._fill_row(index, row)
        layout.addWidget(self._table, 1)

        bulk = QHBoxLayout()
        bulk.setSpacing(8)
        for label_key, action in ((t("import.all_fill"), imp.RowAction.FILL),
                                  (t("import.all_skip_conflicts"), imp.RowAction.SKIP)):
            button = QPushButton(label_key)
            button.setStyleSheet(theme.btn_quiet())
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, a=action: self._set_all_conflicts(a))
            button.setEnabled(bool(preview.conflicts))
            bulk.addWidget(button)
        bulk.addStretch(1)
        layout.addLayout(bulk)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        self._ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok.setText(t("import.apply"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._update_ok()

    def _detected_text(self) -> str:
        if not self.preview.detected:
            return t("common.none")
        return ", ".join(t(f"import.field_{field}") for field in sorted(self.preview.detected))

    def _fill_row(self, index: int, row: imp.ImportRow) -> None:
        state = t("import.state_conflict") if row.is_conflict else t("import.state_new")
        if row.problems:
            state = f"{state} \N{BULLET} {t(row.problems[0], value=row.raw_birthday)}"
        for column, value in enumerate((row.name, birthday_text(row),
                                        row.group or t("common.none"), state)):
            item = QTableWidgetItem(str(value))
            if column == 3 and row.is_conflict:
                from PySide6.QtGui import QColor
                item.setForeground(QColor(theme.color("warnung")))
            self._table.setItem(index, column, item)

        combo = QComboBox()
        for action, label in action_choices(row):
            combo.addItem(label, action.value)
        chosen = combo.findData(imp.RowAction(row.action).value)
        combo.setCurrentIndex(chosen if chosen >= 0 else 0)
        combo.currentIndexChanged.connect(self._update_ok)
        self._combos.append(combo)
        self._table.setCellWidget(index, 4, combo)

    def _set_all_conflicts(self, action: imp.RowAction) -> None:
        for row, combo in zip(self._rows, self._combos):
            if row.is_conflict:
                self.set_action(self._combos.index(combo), action)

    # ── Zustand je Zeile. Ueber diese drei Wege, nicht ueber die Combos: Qt
    #    gibt Nutzerdaten als String zurueck, nicht als Enum.
    def actions_for(self, index: int) -> list[imp.RowAction]:
        combo = self._combos[index]
        return [imp.RowAction(combo.itemData(i)) for i in range(combo.count())]

    def action_at(self, index: int) -> imp.RowAction:
        return imp.RowAction(self._combos[index].currentData())

    def set_action(self, index: int, action: imp.RowAction) -> bool:
        """Waehlt eine Aktion; ``False``, wenn sie fuer die Zeile nicht gilt."""
        found = self._combos[index].findData(imp.RowAction(action).value)
        if found < 0:
            return False
        self._combos[index].setCurrentIndex(found)
        return True

    def _planned(self) -> int:
        return sum(1 for index in range(len(self._combos))
                   if self.action_at(index) is not imp.RowAction.SKIP)

    def _update_ok(self) -> None:
        count = self._planned()
        self._ok.setEnabled(count > 0)
        self._ok.setText(t("import.apply_count", count=count) if count
                         else t("import.apply"))

    def decided_preview(self) -> imp.ImportPreview:
        """Die Vorschau mit den Entscheidungen des Nutzers, sonst unveraendert."""
        for index, row in enumerate(self._rows):
            row.action = self.action_at(index)
        return self.preview


def run_import(parent: QWidget, session_factory, on_done=None) -> None:
    """Vollstaendiger Ablauf: Datei, Vorschau, Bestaetigung, Schreiben.

    ``session_factory`` ist der Kontextmanager ``db.get_session``; der Import
    bekommt bewusst zwei getrennte Sitzungen - die erste liest nur.
    """
    path = choose_file(parent)
    if path is None:
        return
    try:
        headers, rows = imp.read_table(path)
    except imp.ImportError_ as exc:
        QMessageBox.warning(parent, t("import.title"), t(exc.key, **exc.params))
        return
    except OSError as exc:
        QMessageBox.warning(parent, t("import.title"), t("import.unreadable", error=str(exc)))
        return

    with session_factory() as session:
        preview = imp.build_preview(headers, rows, imp.existing_names(session))

    if "name" not in preview.detected and not any(
            key in preview.detected for key in ("first_name", "last_name")):
        QMessageBox.warning(parent, t("import.title"), t("import.no_name_column"))
        return
    if not preview.rows:
        QMessageBox.information(parent, t("import.title"), t("import.empty_file"))
        return

    dialog = ImportPreviewDialog(preview, path, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    with session_factory() as session:
        result = imp.apply_preview(session, dialog.decided_preview())

    message = t("import.done", created=result.created, filled=result.filled,
                skipped=result.skipped)
    if result.failed:
        message = f"{message}\n\n" + "\n".join(result.failed[:10])
    QMessageBox.information(parent, t("import.title"), message)
    if on_done is not None:
        on_done(result)
