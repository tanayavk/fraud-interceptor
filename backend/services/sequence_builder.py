# backend/services/sequence_builder.py
"""
Sequence Builder
Converts raw transaction history + current transaction into
a numpy array of shape (1, max_len, 4) for LSTM input.

Features per timestep: [amount, hour, deviation, velocity]
"""

import numpy as np
from datetime import datetime
from backend.config import SEQUENCE_LENGTH

def build_sequence(transaction: dict, history: list, max_len: int = SEQUENCE_LENGTH) -> np.ndarray:
    """
    Args:
        transaction : dict  - current transaction {"amount": float, "timestamp": float (optional)}
        history     : list  - list of past transaction dicts (oldest first)
        max_len     : int   - LSTM sequence length (default 5)

    Returns:
        np.ndarray of shape (1, max_len, 4), dtype float32
        Columns: [amount, hour, deviation, velocity]
    """
    # Combine history + current, take last max_len
    all_txns = (history + [transaction])[-max_len:]

    # Mean amount over window (for deviation feature)
    amounts = [t.get("amount", 0) for t in all_txns]
    avg_amount = sum(amounts) / len(amounts) if amounts else 1.0

    sequence = []
    for t in all_txns:
        amount = float(t.get("amount", 0))

        timestamp = t.get("timestamp")
        if timestamp:
            hour = float(datetime.fromtimestamp(timestamp).hour)
        else:
            hour = 12.0  # default: midday

        deviation = amount / avg_amount if avg_amount != 0 else 1.0
        velocity  = float(len(all_txns))

        sequence.append([amount, hour, deviation, velocity])

    # Left-pad with zeros if window shorter than max_len
    while len(sequence) < max_len:
        sequence.insert(0, [0.0, 0.0, 0.0, 0.0])

    return np.array(sequence, dtype=np.float32).reshape(1, max_len, 4)