import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import os

# ── CONFIG ────────────────────────────────────────────────────────
SEQ_LEN  = 5
FEATURES = 8  # expanded from 4
N        = 5000

# Features per transaction:
# [amount, hour, amount_deviation, velocity,
#  device_fingerprint, location_consistency, category_risk, account_age]

def generate_data(n_samples=N, seq_len=SEQ_LEN):
    # All values normalized 0-1
    X = np.random.rand(n_samples, seq_len, FEATURES)
    y = np.zeros(n_samples)

    for i in range(n_samples):
        r = np.random.random()

        # FRAUD PATTERN 1: Spike + odd hour + new device
        if r > 0.55:
            X[i, -1, 0] = np.random.uniform(0.85, 1.0)   # high amount
            X[i, -1, 1] = np.random.uniform(0.0, 0.15)   # 2-4 AM
            X[i, -1, 2] = np.random.uniform(0.8, 1.0)    # high deviation
            X[i, -1, 4] = np.random.uniform(0.7, 1.0)    # unknown device
            y[i] = 1

        # FRAUD PATTERN 2: High velocity + location mismatch
        elif r > 0.40:
            X[i, :, 3] = np.random.uniform(0.75, 1.0)    # high velocity all txns
            X[i, -1, 5] = np.random.uniform(0.0, 0.2)    # location mismatch
            y[i] = 1

        # FRAUD PATTERN 3: High risk merchant + new account
        elif r > 0.30:
            X[i, -1, 6] = np.random.uniform(0.8, 1.0)    # crypto/gift card
            X[i, -1, 7] = np.random.uniform(0.0, 0.15)   # very new account
            X[i, -1, 2] = np.random.uniform(0.7, 1.0)    # high deviation
            y[i] = 1

        # FRAUD PATTERN 4: Everything suspicious at once
        elif r > 0.25:
            X[i, -1, 0] = np.random.uniform(0.8, 1.0)    # high amount
            X[i, -1, 4] = np.random.uniform(0.8, 1.0)    # unknown device
            X[i, -1, 5] = np.random.uniform(0.0, 0.2)    # location mismatch
            X[i, -1, 6] = np.random.uniform(0.7, 1.0)    # risky merchant
            X[i, -1, 7] = np.random.uniform(0.0, 0.2)    # new account
            y[i] = 1

    return X, y

# ── DATA ──────────────────────────────────────────────────────────
X, y = generate_data()
print(f"Dataset: {X.shape} | Fraud: {int(y.sum())} | Normal: {int((y==0).sum())}")

# ── MODEL ─────────────────────────────────────────────────────────
model = Sequential([
    LSTM(64, input_shape=(SEQ_LEN, FEATURES), return_sequences=True),
    Dropout(0.2),
    LSTM(32),
    Dropout(0.2),
    Dense(16, activation='relu'),
    Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model.summary()

# ── TRAIN ─────────────────────────────────────────────────────────
model.fit(X, y, epochs=15, batch_size=32, validation_split=0.2, verbose=1)

# ── SAVE ──────────────────────────────────────────────────────────
os.makedirs('ml/model', exist_ok=True)
model.save('ml/model/lstm_model.h5')
print("✅ Model saved to ml/model/lstm_model.h5")