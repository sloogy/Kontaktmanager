# db.py

import sqlite3
import os

class Database:
    _connection = None
    _cursor = None

    @staticmethod
    def initialize_database(db_path='termine.db'):
        db_exists = os.path.exists(db_path)
        Database._connection = sqlite3.connect(db_path)
        Database._cursor = Database._connection.cursor()
        if not db_exists:
            cursor = Database._cursor
            # Tabellen erstellen
            cursor.execute("""
                CREATE TABLE kontakte (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    gruppe TEXT,
                    beziehungsgrad TEXT,
                    letztes_treffen TEXT,
                    naechstes_treffen TEXT,
                    geplantes_treffen TEXT,
                    notizen TEXT,
                    ist_gebucht INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE beziehungsgrade (
                    beziehungsgrad TEXT PRIMARY KEY,
                    exclude_3_day_rule INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE groups (
                    gruppe TEXT PRIMARY KEY
                )
            """)
            cursor.execute("""
                CREATE TABLE settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            # Standard-Einstellungen einfügen
            cursor.executemany("""
                INSERT INTO settings (key, value) VALUES (?, ?)
            """, [
                ('function_active', '0'),
                ('only_every_active', '0'),
                ('only_every_number', '1'),
                ('only_every_unit', 'Wochenende'),
                ('max_days_per_week_active', '0'),
                ('max_days_per_week', '5'),
                ('max_weekends_per_month_active', '0'),
                ('max_weekends_per_month', '4'),
                ('allowed_weekdays_active', '0'),
                ('allowed_weekdays', '0,1,2,3,4'),
            ])
            # Standard-Gruppen einfügen
            cursor.execute("""
                INSERT INTO groups (gruppe) VALUES
                ('Unbekannt'), ('Freunde'), ('Familie'), ('Arbeit')
            """)
            # Standard-Beziehungsgrade einfügen
            cursor.execute("""
                INSERT INTO beziehungsgrade (beziehungsgrad) VALUES
                ('Bekannter'), ('Freund'), ('Familie')
            """)
            Database._connection.commit()
        else:
            # Stellen Sie sicher, dass alle Einstellungen vorhanden sind
            Database.ensure_settings_keys()

    @staticmethod
    def ensure_settings_keys():
        cursor = Database.get_cursor()
        existing_keys = set()
        cursor.execute("SELECT key FROM settings")
        for row in cursor.fetchall():
            existing_keys.add(row[0])

        # Benötigte Einstellungen mit Standardwerten
        required_settings = {
            'function_active': '0',
            'only_every_active': '0',
            'only_every_number': '1',
            'only_every_unit': 'Wochenende',
            'max_days_per_week_active': '0',
            'max_days_per_week': '5',
            'max_weekends_per_month_active': '0',
            'max_weekends_per_month': '4',
            'allowed_weekdays_active': '0',
            'allowed_weekdays': '0,1,2,3,4',
        }

        # Fehlende Einstellungen hinzufügen
        for key, value in required_settings.items():
            if key not in existing_keys:
                cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))

        Database.get_connection().commit()

    @staticmethod
    def get_connection():
        return Database._connection

    @staticmethod
    def get_cursor():
        return Database._cursor

    @staticmethod
    def close_connection():
        if Database._connection:
            Database._connection.close()
            Database._connection = None
            Database._cursor = None
            