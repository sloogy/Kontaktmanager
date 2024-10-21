# main.py

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QComboBox, QDialogButtonBox, QPlainTextEdit, QPushButton,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QSpinBox, QTableView
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction
from PySide6.QtCore import Qt
from db import Database
from Kontaktmanager_ui import Ui_MainWindow  # Importiert das generierte UI-Design
from datetime import datetime

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        Database.initialize_database()
        self.selected_contact_id = None  # Initialisierung

        self.connect_signals()
        self.load_contacts()
        self.load_beziehungsgrade()
        self.load_gruppen()

        # Menüaktion für Globale Einstellungen hinzufügen
        self.actionGlobale_Einstellungen.triggered.connect(self.open_global_settings)

    def connect_signals(self):
        # Suchfeld
        self.plainTextEditkontaktsuche.textChanged.connect(self.update_contact_filter)

        # Kontakt hinzufügen
        self.pushButton_4.clicked.connect(self.add_contact)

        # Kontakt bearbeiten
        self.pushButton_5.clicked.connect(self.edit_contact)

        # Kontakt löschen
        self.pushButton_6.clicked.connect(self.delete_contact)

        # Tabelle der Kontakte
        self.tableViewKontakteliste.clicked.connect(self.on_contact_selected)

        # Beziehungsgrade Buttons
        self.pushButton_12.clicked.connect(self.edit_beziehungsgrad)
        self.pushButton_10.clicked.connect(self.add_beziehungsgrad)
        self.pushButton_11.clicked.connect(self.delete_beziehungsgrad)

        # Gruppen Buttons
        self.pushButton_14.clicked.connect(self.edit_gruppe)
        self.pushButton_13.clicked.connect(self.add_gruppe)
        self.pushButton_15.clicked.connect(self.delete_gruppe)

    def open_global_settings(self):
        dialog = GlobalSettingsDialog(self)
        dialog.exec()

    def load_contacts(self):
        self.contact_model = QStandardItemModel()
        self.contact_model.setHorizontalHeaderLabels(['ID', 'Name', 'Gruppe', 'Beziehungsgrad'])
        cursor = Database.get_cursor()
        cursor.execute('SELECT id, name, gruppe, beziehungsgrad FROM kontakte')
        rows = cursor.fetchall()
        self.contact_data = []  # Liste zum Speichern der Daten
        for row in rows:
            self.contact_data.append(row)  # Daten speichern
            items = [QStandardItem(str(field)) for field in row]
            self.contact_model.appendRow(items)
        self.tableViewKontakteliste.setModel(self.contact_model)
        self.tableViewKontakteliste.resizeColumnsToContents()

    def update_contact_filter(self):
        text = self.plainTextEditkontaktsuche.toPlainText().strip().lower()
        if not text:
            # Wenn das Suchfeld leer ist, zeigen Sie alle Kontakte an
            self.tableViewKontakteliste.setModel(self.contact_model)
            self.tableViewKontakteliste.resizeColumnsToContents()
            return

        filtered_model = QStandardItemModel()
        filtered_model.setHorizontalHeaderLabels(['ID', 'Name', 'Gruppe', 'Beziehungsgrad'])

        search_terms = text.split()  # Suchtext in Wörter aufteilen

        for row in self.contact_data:
            id_, name, gruppe, beziehungsgrad = row
            # Kombinieren Sie die durchsuchbaren Felder in einem String
            searchable_text = f"{name} {gruppe} {beziehungsgrad}".lower()
            # Überprüfen Sie, ob alle Suchbegriffe in den durchsuchbaren Text passen
            if all(term in searchable_text for term in search_terms):
                items = [QStandardItem(str(field)) for field in row]
                filtered_model.appendRow(items)

        self.tableViewKontakteliste.setModel(filtered_model)
        self.tableViewKontakteliste.resizeColumnsToContents()

    def on_contact_selected(self, index):
        self.selected_contact_id = int(self.tableViewKontakteliste.model().item(index.row(), 0).text())

    def add_contact(self):
        dialog = ContactDialog(mode='add', parent=self)
        if dialog.exec():
            self.load_contacts()

    def edit_contact(self):
        if self.selected_contact_id is None:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Kontakt aus.")
            return
        dialog = ContactDialog(mode='edit', contact_id=self.selected_contact_id, parent=self)
        if dialog.exec():
            self.load_contacts()

    def delete_contact(self):
        if self.selected_contact_id is None:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Kontakt aus.")
            return
        confirm = QMessageBox.question(self, "Bestätigung", "Möchten Sie diesen Kontakt wirklich löschen?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            cursor = Database.get_cursor()
            cursor.execute('DELETE FROM kontakte WHERE id = ?', (self.selected_contact_id,))
            Database.get_connection().commit()
            self.load_contacts()
            self.selected_contact_id = None  # Zurücksetzen

    def load_beziehungsgrade(self):
        self.beziehungsgrad_model = QStandardItemModel()
        self.beziehungsgrad_model.setHorizontalHeaderLabels(['Beziehungsgrad'])
        cursor = Database.get_cursor()
        cursor.execute('SELECT beziehungsgrad FROM beziehungsgrade')
        rows = cursor.fetchall()
        self.beziehungsgrad_data = []  # Daten speichern
        for row in rows:
            self.beziehungsgrad_data.append(row[0])
            item = QStandardItem(row[0])
            self.beziehungsgrad_model.appendRow(item)
        self.tableViewTAG.setModel(self.beziehungsgrad_model)
        self.tableViewTAG.resizeColumnsToContents()

    def add_beziehungsgrad(self):
        dialog = BeziehungsgradDialog(mode='add', parent=self)
        if dialog.exec():
            self.load_beziehungsgrade()

    def edit_beziehungsgrad(self):
        selected_indexes = self.tableViewTAG.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Beziehungsgrad aus.")
            return
        beziehungsgrad = self.beziehungsgrad_model.item(selected_indexes[0].row(), 0).text()
        dialog = BeziehungsgradDialog(mode='edit', beziehungsgrad=beziehungsgrad, parent=self)
        if dialog.exec():
            self.load_beziehungsgrade()

    def delete_beziehungsgrad(self):
        selected_indexes = self.tableViewTAG.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Beziehungsgrad aus.")
            return
        beziehungsgrad = self.beziehungsgrad_model.item(selected_indexes[0].row(), 0).text()
        confirm = QMessageBox.question(self, "Bestätigung", f"Möchten Sie den Beziehungsgrad '{beziehungsgrad}' wirklich löschen?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            cursor = Database.get_cursor()
            cursor.execute('DELETE FROM beziehungsgrade WHERE beziehungsgrad = ?', (beziehungsgrad,))
            Database.get_connection().commit()
            self.load_beziehungsgrade()

    def load_gruppen(self):
        self.gruppen_model = QStandardItemModel()
        self.gruppen_model.setHorizontalHeaderLabels(['Gruppe'])
        cursor = Database.get_cursor()
        cursor.execute('SELECT gruppe FROM groups')
        rows = cursor.fetchall()
        self.gruppen_data = []  # Daten speichern
        for row in rows:
            self.gruppen_data.append(row[0])
            item = QStandardItem(row[0])
            self.gruppen_model.appendRow(item)
        self.tableViewTAG_2.setModel(self.gruppen_model)
        self.tableViewTAG_2.resizeColumnsToContents()

    def add_gruppe(self):
        dialog = GruppeDialog(mode='add', parent=self)
        if dialog.exec():
            self.load_gruppen()

    def edit_gruppe(self):
        selected_indexes = self.tableViewTAG_2.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie eine Gruppe aus.")
            return
        gruppe = self.gruppen_model.item(selected_indexes[0].row(), 0).text()
        dialog = GruppeDialog(mode='edit', gruppe=gruppe, parent=self)
        if dialog.exec():
            self.load_gruppen()

    def delete_gruppe(self):
        selected_indexes = self.tableViewTAG_2.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie eine Gruppe aus.")
            return
        gruppe = self.gruppen_model.item(selected_indexes[0].row(), 0).text()
        confirm = QMessageBox.question(self, "Bestätigung", f"Möchten Sie die Gruppe '{gruppe}' wirklich löschen?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            cursor = Database.get_cursor()
            cursor.execute('DELETE FROM groups WHERE gruppe = ?', (gruppe,))
            Database.get_connection().commit()
            self.load_gruppen()

class GlobalSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Globale Einstellungen")
        self.setup_ui()
        self.load_settings()
        self.connect_signals()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Aktivierungscheckbox für "Nur jedes ... Tage/Wochenende"
        self.only_every_active_checkbox = QCheckBox("Aktivieren")
        layout.addWidget(self.only_every_active_checkbox)

        # Option "nur jedes [Zahl] [Dropdown]"
        function_layout = QHBoxLayout()
        self.only_every_spinbox = QSpinBox()
        self.only_every_spinbox.setMinimum(1)
        self.only_every_combobox = QComboBox()
        self.only_every_combobox.addItems(["Wochenende", "Tag"])
        function_layout.addWidget(QLabel("Nur jedes"))
        function_layout.addWidget(self.only_every_spinbox)
        function_layout.addWidget(self.only_every_combobox)
        layout.addLayout(function_layout)

        # Aktivierungscheckbox für "Maximale Tage unter der Woche"
        self.max_days_per_week_active_checkbox = QCheckBox("Aktivieren")
        layout.addWidget(self.max_days_per_week_active_checkbox)

        # Maximale Tage unter der Woche
        max_days_layout = QHBoxLayout()
        self.max_days_spinbox = QSpinBox()
        self.max_days_spinbox.setRange(1, 5)  # Unter der Woche gibt es maximal 5 Tage
        max_days_layout.addWidget(QLabel("Maximale Tage unter der Woche:"))
        max_days_layout.addWidget(self.max_days_spinbox)
        layout.addLayout(max_days_layout)

        # Aktivierungscheckbox für "Maximale Wochenenden"
        self.max_weekends_per_month_active_checkbox = QCheckBox("Aktivieren")
        layout.addWidget(self.max_weekends_per_month_active_checkbox)

        # Maximale Wochenenden pro Monat
        max_weekends_layout = QHBoxLayout()
        self.max_weekends_spinbox = QSpinBox()
        self.max_weekends_spinbox.setRange(0, 5)
        max_weekends_layout.addWidget(QLabel("Maximale Wochenenden pro Monat:"))
        max_weekends_layout.addWidget(self.max_weekends_spinbox)
        layout.addLayout(max_weekends_layout)

        # Aktivierungscheckbox für "Erlaubte Wochentage"
        self.allowed_weekdays_active_checkbox = QCheckBox("Aktivieren")
        layout.addWidget(self.allowed_weekdays_active_checkbox)

        # Auswahl der erlaubten Wochentage
        self.weekday_checkboxes = []
        weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        layout.addWidget(QLabel("Erlaubte Wochentage:"))
        weekdays_layout = QHBoxLayout()
        for i, day in enumerate(weekdays):
            checkbox = QCheckBox(day)
            checkbox.weekday = i  # Speichern Sie den Wochentag (0 = Montag)
            weekdays_layout.addWidget(checkbox)
            self.weekday_checkboxes.append(checkbox)
        layout.addLayout(weekdays_layout)

        # Speichern-Button
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def connect_signals(self):
        # Aktivierungscheckboxen verbinden
        self.only_every_active_checkbox.stateChanged.connect(self.update_fields_state)
        self.max_days_per_week_active_checkbox.stateChanged.connect(self.update_fields_state)
        self.max_weekends_per_month_active_checkbox.stateChanged.connect(self.update_fields_state)
        self.allowed_weekdays_active_checkbox.stateChanged.connect(self.update_fields_state)

    def update_fields_state(self):
        # "Nur jedes ... Tage/Wochenende"
        only_every_active = self.only_every_active_checkbox.isChecked()
        self.only_every_spinbox.setEnabled(only_every_active)
        self.only_every_combobox.setEnabled(only_every_active)

        # "Maximale Tage unter der Woche"
        max_days_active = self.max_days_per_week_active_checkbox.isChecked()
        self.max_days_spinbox.setEnabled(max_days_active)

        # "Maximale Wochenenden"
        max_weekends_active = self.max_weekends_per_month_active_checkbox.isChecked()
        self.max_weekends_spinbox.setEnabled(max_weekends_active)

        # "Erlaubte Wochentage"
        allowed_weekdays_active = self.allowed_weekdays_active_checkbox.isChecked()
        for cb in self.weekday_checkboxes:
            cb.setEnabled(allowed_weekdays_active)

    def load_settings(self):
        cursor = Database.get_cursor()

        # "Nur jedes ... Tage/Wochenende"
        cursor.execute("SELECT value FROM settings WHERE key = 'only_every_active'")
        result = cursor.fetchone()
        self.only_every_active_checkbox.setChecked(result and result[0] == '1')

        cursor.execute("SELECT value FROM settings WHERE key = 'only_every_number'")
        result = cursor.fetchone()
        if result:
            self.only_every_spinbox.setValue(int(result[0]))

        cursor.execute("SELECT value FROM settings WHERE key = 'only_every_unit'")
        result = cursor.fetchone()
        if result:
            index = self.only_every_combobox.findText(result[0])
            if index >= 0:
                self.only_every_combobox.setCurrentIndex(index)

        # "Maximale Tage unter der Woche"
        cursor.execute("SELECT value FROM settings WHERE key = 'max_days_per_week_active'")
        result = cursor.fetchone()
        self.max_days_per_week_active_checkbox.setChecked(result and result[0] == '1')

        cursor.execute("SELECT value FROM settings WHERE key = 'max_days_per_week'")
        result = cursor.fetchone()
        if result:
            self.max_days_spinbox.setValue(int(result[0]))

        # "Maximale Wochenenden"
        cursor.execute("SELECT value FROM settings WHERE key = 'max_weekends_per_month_active'")
        result = cursor.fetchone()
        self.max_weekends_per_month_active_checkbox.setChecked(result and result[0] == '1')

        cursor.execute("SELECT value FROM settings WHERE key = 'max_weekends_per_month'")
        result = cursor.fetchone()
        if result:
            self.max_weekends_spinbox.setValue(int(result[0]))

        # "Erlaubte Wochentage"
        cursor.execute("SELECT value FROM settings WHERE key = 'allowed_weekdays_active'")
        result = cursor.fetchone()
        self.allowed_weekdays_active_checkbox.setChecked(result and result[0] == '1')

        cursor.execute("SELECT value FROM settings WHERE key = 'allowed_weekdays'")
        result = cursor.fetchone()
        if result:
            allowed_days = [int(day) for day in result[0].split(',') if day]
            for checkbox in self.weekday_checkboxes:
                if checkbox.weekday in allowed_days:
                    checkbox.setChecked(True)
                else:
                    checkbox.setChecked(False)

        # Felder entsprechend aktivieren oder deaktivieren
        self.update_fields_state()

    def save_settings(self):
        cursor = Database.get_cursor()
        conn = Database.get_connection()

        # "Nur jedes ... Tage/Wochenende"
        only_every_active = '1' if self.only_every_active_checkbox.isChecked() else '0'
        cursor.execute("REPLACE INTO settings (key, value) VALUES ('only_every_active', ?)", (only_every_active,))
        only_every_number = self.only_every_spinbox.value()
        cursor.execute("REPLACE INTO settings (key, value) VALUES ('only_every_number', ?)", (str(only_every_number),))
        only_every_unit = self.only_every_combobox.currentText()
        cursor.execute("REPLACE INTO settings (key, value) VALUES ('only_every_unit', ?)", (only_every_unit,))

        # "Maximale Tage unter der Woche"
        max_days_active = '1' if self.max_days_per_week_active_checkbox.isChecked() else '0'
        cursor.execute("REPLACE INTO settings (key, value) VALUES ('max_days_per_week_active', ?)", (max_days_active,))
        max_days = self.max_days_spinbox.value()
        cursor.execute("REPLACE INTO settings (key, value) VALUES ('max_days_per_week', ?)", (str(max_days),))

        # "Maximale Wochenenden"
        max_weekends_active = '1' if self.max_weekends_per_month_active_checkbox.isChecked() else '0'
        cursor.execute("REPLACE INTO settings (key, value) VALUES ('max_weekends_per_month_active', ?)", (max_weekends_active,))
        max_weekends = self.max_weekends_spinbox.value()
        cursor.execute("REPLACE INTO settings (key, value) VALUES ('max_weekends_per_month', ?)", (str(max_weekends),))

        # "Erlaubte Wochentage"
        allowed_weekdays_active = '1' if self.allowed_weekdays_active_checkbox.isChecked() else '0'
        cursor.execute("REPLACE INTO settings (key, value) VALUES ('allowed_weekdays_active', ?)", (allowed_weekdays_active,))
        allowed_days = [str(cb.weekday) for cb in self.weekday_checkboxes if cb.isChecked()]
        allowed_days_str = ','.join(allowed_days)
        cursor.execute("REPLACE INTO settings (key, value) VALUES ('allowed_weekdays', ?)", (allowed_days_str,))

        conn.commit()
        QMessageBox.information(self, "Erfolg", "Einstellungen wurden gespeichert.")
        self.accept()

class ContactDialog(QDialog):
    # Ihr vorhandener Code für ContactDialog bleibt unverändert

    def __init__(self, mode='add', contact_id=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.contact_id = contact_id
        self.setWindowTitle("Kontakt hinzufügen" if mode == 'add' else "Kontakt bearbeiten")
        self.setup_ui()
        if mode == 'edit':
            self.load_contact_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.name_input = QLineEdit()
        self.gruppe_input = QComboBox()
        self.load_gruppen()
        self.beziehungsgrad_input = QComboBox()
        self.load_beziehungsgrade()
        self.letztes_treffen_input = QLineEdit()
        self.notizen_input = QPlainTextEdit()

        layout.addRow("Name:", self.name_input)
        layout.addRow("Gruppe:", self.gruppe_input)
        layout.addRow("Beziehungsgrad:", self.beziehungsgrad_input)
        layout.addRow("Letztes Treffen (dd.mm.yyyy):", self.letztes_treffen_input)
        layout.addRow("Notizen:", self.notizen_input)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_contact)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_gruppen(self):
        cursor = Database.get_cursor()
        cursor.execute('SELECT gruppe FROM groups')
        gruppen = [row[0] for row in cursor.fetchall()]
        self.gruppe_input.addItems(gruppen)

    def load_beziehungsgrade(self):
        cursor = Database.get_cursor()
        cursor.execute('SELECT beziehungsgrad FROM beziehungsgrade')
        beziehungsgrade = [row[0] for row in cursor.fetchall()]
        self.beziehungsgrad_input.addItems(beziehungsgrade)

    def load_contact_data(self):
        cursor = Database.get_cursor()
        cursor.execute('SELECT name, gruppe, beziehungsgrad, letztes_treffen, notizen FROM kontakte WHERE id = ?', (self.contact_id,))
        result = cursor.fetchone()
        if result:
            self.name_input.setText(result[0])
            self.gruppe_input.setCurrentText(result[1])
            self.beziehungsgrad_input.setCurrentText(result[2])
            self.letztes_treffen_input.setText(result[3] if result[3] else '')
            self.notizen_input.setPlainText(result[4] if result[4] else '')
        else:
            QMessageBox.warning(self, "Fehler", "Kontakt nicht gefunden.")
            self.reject()

    def save_contact(self):
        name = self.name_input.text()
        gruppe = self.gruppe_input.currentText()
        beziehungsgrad = self.beziehungsgrad_input.currentText()
        letztes_treffen = self.letztes_treffen_input.text()
        notizen = self.notizen_input.toPlainText()

        if not name:
            QMessageBox.warning(self, "Fehler", "Name darf nicht leer sein.")
            return

        # Validierung des Datums
        try:
            if letztes_treffen:
                datetime.strptime(letztes_treffen, '%d.%m.%Y')
        except ValueError:
            QMessageBox.warning(self, "Fehler", "Ungültiges Datum. Bitte im Format dd.mm.yyyy eingeben.")
            return

        cursor = Database.get_cursor()
        if self.mode == 'add':
            cursor.execute('''
                INSERT INTO kontakte (name, gruppe, beziehungsgrad, letztes_treffen, notizen)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, gruppe, beziehungsgrad, letztes_treffen, notizen))
        else:
            cursor.execute('''
                UPDATE kontakte SET name = ?, gruppe = ?, beziehungsgrad = ?, letztes_treffen = ?, notizen = ?
                WHERE id = ?
            ''', (name, gruppe, beziehungsgrad, letztes_treffen, notizen, self.contact_id))
        Database.get_connection().commit()
        self.accept()

class BeziehungsgradDialog(QDialog):
    # Ihr vorhandener Code für BeziehungsgradDialog bleibt unverändert

    def __init__(self, mode='add', beziehungsgrad=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.beziehungsgrad = beziehungsgrad
        self.setWindowTitle("Beziehungsgrad hinzufügen" if mode == 'add' else "Beziehungsgrad bearbeiten")
        self.setup_ui()
        if mode == 'edit':
            self.load_beziehungsgrad_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.beziehungsgrad_input = QLineEdit()
        layout.addRow("Beziehungsgrad:", self.beziehungsgrad_input)
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_beziehungsgrad)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_beziehungsgrad_data(self):
        self.beziehungsgrad_input.setText(self.beziehungsgrad)

    def save_beziehungsgrad(self):
        beziehungsgrad = self.beziehungsgrad_input.text()
        if not beziehungsgrad:
            QMessageBox.warning(self, "Fehler", "Beziehungsgrad darf nicht leer sein.")
            return
        cursor = Database.get_cursor()
        if self.mode == 'add':
            cursor.execute('INSERT INTO beziehungsgrade (beziehungsgrad) VALUES (?)', (beziehungsgrad,))
        else:
            cursor.execute('''
                UPDATE beziehungsgrade SET beziehungsgrad = ?
                WHERE beziehungsgrad = ?
            ''', (beziehungsgrad, self.beziehungsgrad))
        Database.get_connection().commit()
        self.accept()

class GruppeDialog(QDialog):
    # Ihr vorhandener Code für GruppeDialog bleibt unverändert

    def __init__(self, mode='add', gruppe=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.gruppe = gruppe
        self.setWindowTitle("Gruppe hinzufügen" if mode == 'add' else "Gruppe bearbeiten")
        self.setup_ui()
        if mode == 'edit':
            self.load_gruppe_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.gruppe_input = QLineEdit()
        layout.addRow("Gruppe:", self.gruppe_input)
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_gruppe)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_gruppe_data(self):
        self.gruppe_input.setText(self.gruppe)

    def save_gruppe(self):
        gruppe = self.gruppe_input.text()
        if not gruppe:
            QMessageBox.warning(self, "Fehler", "Gruppe darf nicht leer sein.")
            return
        cursor = Database.get_cursor()
        if self.mode == 'add':
            cursor.execute('INSERT INTO groups (gruppe) VALUES (?)', (gruppe,))
        else:
            cursor.execute('''
                UPDATE groups SET gruppe = ?
                WHERE gruppe = ?
            ''', (gruppe, self.gruppe))
        Database.get_connection().commit()
        self.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
