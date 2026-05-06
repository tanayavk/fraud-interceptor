import sqlite3
import numpy as np

DB_PATH = 'backend/transactions.db'

def get_user_sequence(user_id, window_size=5):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Updated: 8 features now
        query = """
            SELECT Amount_INR, Hour, Amount_Deviation, Transaction_Frequency,
                   Device_Fingerprint, Location_Consistency, Category_Risk, Account_Age
            FROM transactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        cursor.execute(query, (user_id, window_size))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        sequence = list(reversed(rows))

        # Pad with 8 zeros now
        if len(sequence) < window_size:
            padding = [[0.0] * 8] * (window_size - len(sequence))
            sequence = padding + sequence

        return sequence

    except Exception as e:
        print(f"Error building sequence: {e}")
        return []