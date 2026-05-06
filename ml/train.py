import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# 1. Synthetic Data Generation (Sequences of N=5 transactions)
def generate_data(n_samples=5000, seq_len=5):
    X = np.random.rand(n_samples, seq_len, 4) # [amount, hour, deviation, velocity]
    y = np.zeros(n_samples)
    
    for i in range(n_samples):
        # Fraud Pattern 1: Sudden spike in amount + odd timing
        if np.random.random() > 0.5:
            X[i, -1, 0] = np.random.uniform(0.8, 1.0) # High Amount
            X[i, -1, 1] = np.random.uniform(0.0, 0.2) # 2AM - 4AM
            y[i] = 1
        # Fraud Pattern 2: High velocity in sequence
        elif np.random.random() > 0.7:
            X[i, :, 3] = np.random.uniform(0.7, 1.0) # High velocity across sequence
            y[i] = 1
            
    return X, y

# 2. Build Lightweight LSTM
X, y = generate_data()
model = Sequential([
    LSTM(32, input_shape=(5, 4), activation='tanh'),
    Dropout(0.2),
    Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# 3. Train and Save
model.fit(X, y, epochs=10, batch_size=32, verbose=0)
model.save('ml/model/lstm_model.h5')
print("Model saved to ml/model/lstm_model.h5")