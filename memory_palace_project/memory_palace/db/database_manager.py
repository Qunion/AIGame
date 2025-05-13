import sqlite3
from pathlib import Path

class DatabaseManager:
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent / 'data' / 'database' / 'memory_palace.sqlite'
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        return self.conn.cursor()

    def initialize_db(self):
        cursor = self.connect()
        cursor.execute('''CREATE TABLE IF NOT EXISTS timelines
                        (id TEXT PRIMARY KEY, name TEXT, created_at DATETIME)''')
        self.conn.commit()
        self.conn.close()