import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'transactions.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            Amount_INR REAL NOT NULL,
            Hour INTEGER NOT NULL,
            Amount_Deviation REAL DEFAULT 0.0,
            Transaction_Frequency REAL DEFAULT 0.0,
            Device_Fingerprint REAL DEFAULT 0.5,
            Location_Consistency REAL DEFAULT 1.0,
            Category_Risk REAL DEFAULT 0.1,
            Account_Age REAL DEFAULT 1.0,
            device_id TEXT,
            location_city TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 8 features matching new schema
    seed_data = [
        ('nandan_001', 450.0,  10, 0.1, 0.2, 0.9, 1.0, 0.1, 0.8, 'iphone_15', 'Bengaluru'),
        ('nandan_001', 1200.0, 12, 0.3, 0.3, 0.9, 1.0, 0.2, 0.8, 'iphone_15', 'Bengaluru'),
        ('nandan_001', 300.0,  15, 0.0, 0.1, 0.9, 1.0, 0.1, 0.8, 'iphone_15', 'Bengaluru'),
        ('nandan_001', 2500.0, 18, 0.6, 0.4, 0.9, 1.0, 0.4, 0.8, 'iphone_15', 'Bengaluru'),
        ('nandan_001', 150.0,  21, 0.0, 0.1, 0.9, 1.0, 0.1, 0.8, 'iphone_15', 'Bengaluru'),
    ]

    cursor.executemany('''
        INSERT INTO transactions (
            user_id, Amount_INR, Hour, Amount_Deviation, Transaction_Frequency,
            Device_Fingerprint, Location_Consistency, Category_Risk, Account_Age,
            device_id, location_city
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', seed_data)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")