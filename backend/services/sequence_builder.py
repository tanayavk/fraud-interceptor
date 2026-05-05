import sqlite3
import numpy as np

DB_PATH = 'backend/transactions.db'

def get_user_sequence(user_id, window_size=5):
    """
    Fetches the last N transactions for a user and formats them for the LSTM.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Query the last N transactions for this specific user
        # Features: Amount, Hour, Geo_Distance, Merchant_Risk
        query = """
            SELECT Amount_INR, Hour, Geo_Distance_km, Merchant_Risk_Score 
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

        # Reverse so the sequence is in chronological order (Oldest -> Newest)
        sequence = list(reversed(rows))

        # Padding logic: If user has < 5 transactions, pad with zeros
        # This prevents the LSTM from crashing on new users
        if len(sequence) < window_size:
            padding = [[0.0, 0.0, 0.0, 0.0]] * (window_size - len(sequence))
            sequence = padding + sequence

        return sequence

    except Exception as e:
        print(f"Error building sequence: {e}")
        return []