import numpy as np
import joblib
from sklearn.preprocessing import MinMaxScaler

# Features: [Amount_INR, Hour, Amount_Deviation, Transaction_Frequency]
SCALER_PATH = 'ml/model/scaler.pkl'

def scale_features(raw_data, fit=False):
    """
    Normalizes features to a 0-1 range. 
    LSTMs are sensitive to scale; ₹1,00,000 and 2 AM need to be on the same scale.
    """
    if fit:
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(raw_data)
        joblib.dump(scaler, SCALER_PATH)
        return scaled_data
    else:
        scaler = joblib.load(SCALER_PATH)
        return scaler.transform(raw_data)

def create_lstm_sequences(data, window_size=5):
    """
    Converts flat rows into overlapping sequences.
    If you have 10 transactions, this creates 'windows' of 5 to show behavior trends.
    """
    sequences = []
    for i in range(len(data) - window_size + 1):
        sequences.append(data[i:i+window_size])
    return np.array(sequences)

def handle_missing_data(df):
    """
    Failsafe: Fills empty values so the model doesn't crash.
    """
    return df.fillna(0)