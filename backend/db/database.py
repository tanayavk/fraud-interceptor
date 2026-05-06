import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'transactions.db')

def get_db_connection():
    """Returns a connection object to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Initializes the database schema and inserts seed data."""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create the table with specific features for the project
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            Amount_INR REAL NOT NULL,
            Hour INTEGER NOT NULL,
            Geo_Distance_km REAL NOT NULL,
            Merchant_Risk_Score REAL NOT NULL,
            device_id TEXT,
            location_city TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Add seed data for "nandan_001" to satisfy the LSTM sequence window of 5
    seed_data = [
        ('nandan_001', 450.0, 10, 2.5, 0.1, 'iphone_15', 'Bengaluru'),
        ('nandan_001', 1200.0, 12, 5.0, 0.2, 'iphone_15', 'Bengaluru'),
        ('nandan_001', 300.0, 15, 1.2, 0.1, 'iphone_15', 'Bengaluru'),
        ('nandan_001', 2500.0, 18, 15.0, 0.4, 'iphone_15', 'Bengaluru'),
        ('nandan_001', 150.0, 21, 0.8, 0.1, 'iphone_15', 'Bengaluru')
    ]

    cursor.executemany('''
        INSERT INTO transactions (user_id, Amount_INR, Hour, Geo_Distance_km, Merchant_Risk_Score, device_id, location_city)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', seed_data)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")