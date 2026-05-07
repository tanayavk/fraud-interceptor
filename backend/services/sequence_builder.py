# import numpy as np
# from backend.config import SEQUENCE_LENGTH

# def build_sequence(current_tx, history, max_len=5):
#     """
#     Converts raw transaction history into a (1, 5, 8) tensor.
#     """
#     def extract_features(tx):
#         # Must match the 8-feature order exactly as trained:
#         # [Amount, Hour, Deviation, Frequency, Device, Location, Category, Age]
#         return [
#             float(tx.get("amount", 0.0)),
#             float(tx.get("hour", 0.0)),
#             float(tx.get("amount_deviation", 0.0)),
#             float(tx.get("frequency", 1.0)),
#             int(tx.get("device_fingerprint", 1)),
#             int(tx.get("location_consistency", 1)),
#             float(tx.get("category_risk", 0.1)),
#             int(tx.get("account_age", 365))
#         ]

#     # 1. Map history to feature lists
#     sequence = [extract_features(tx) for tx in history]

#     # 2. Add current transaction to the end
#     sequence.append(extract_features(current_tx))

#     # 3. Trim or Pad (Ensure length is exactly max_len)
#     if len(sequence) > max_len:
#         sequence = sequence[-max_len:]
#     else:
#         padding = [[0.0] * 8] * (max_len - len(sequence))
#         sequence = padding + sequence

#     return sequence


import numpy as np
import joblib
import os
from backend.config import SEQUENCE_LENGTH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SCALER_PATH = os.path.join(BASE_DIR, 'ml', 'model', 'scaler.pkl')

def build_sequence(current_tx, history, max_len=5):
    """
    Transforms raw transaction data into a scaled sequence for the LSTM.
    """
    def extract_features(tx):
        # EXACT ORDER PROVIDED BY USER:
        # [Amount, Hour, Z-Score, Frequency, Device, Location, Category, Age]
        return [
            float(tx.get("amount", 0.0)),
            float(tx.get("hour", 0.0)),
            float(tx.get("amount_zscore", 0.0)),
            float(tx.get("tx_frequency_60m", 0.0)),
            float(tx.get("device_fingerprint", 1.0)),
            float(tx.get("location_consistency", 1.0)),
            float(tx.get("category_risk", 0.1)),
            float(tx.get("account_age_days", 365))
        ]

    # 1. Map history to raw features
    raw_sequence = [extract_features(tx) for tx in history]
    raw_sequence.append(extract_features(current_tx))

    # 2. Pad/Trim to exact window size
    if len(raw_sequence) > max_len:
        raw_sequence = raw_sequence[-max_len:]
    else:
        padding = [[0.0] * 8] * (max_len - len(raw_sequence))
        raw_sequence = padding + raw_sequence

    # 3. Flatten for the Scaler (Transform 5x8 into 1x40)
    try:
        scaler = joblib.load(SCALER_PATH)
        flattened_raw = np.array(raw_sequence).reshape(1, -1) # 1 row, 40 columns
        scaled_flattened = scaler.transform(flattened_raw)
        
        # 4. Reshape back to 3D for LSTM (1, 5, 8)
        final_seq = scaled_flattened.reshape(5, 8)
        return final_seq.tolist()
    except Exception as e:
        print(f"❌ Scaling failed: {e}")
        return raw_sequence # Fallback