import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'transactions.db')

def get_db_connection():
    """Returns a connection object to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    # Allows accessing columns by name like row['Amount_INR']
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Initializes the database schema if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create transactions table matching your 8-parameter plan
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
    conn.commit()
    conn.close()