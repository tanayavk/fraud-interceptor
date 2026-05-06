import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # disable oneDNN custom ops
import tensorflow as tf
import numpy as np
from joblib import load


# Build robust paths relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MODEL_PATH     = os.path.join(BASE_DIR, 'ml', 'model', 'lstm_model.h5')
SCALER_PATH    = os.path.join(BASE_DIR, 'ml', 'model', 'scaler.pkl')


def predict(sequence):
    try:
        print("✅ lstm_service.py: predict(sequence) called")
        print("Input sequence shape:", np.array(sequence).shape)

        if not os.path.exists(MODEL_PATH):
            print(f"❌ Model not found at: {MODEL_PATH}")
            return {"dl_score": 0.5}

        if not os.path.exists(SCALER_PATH):
            print(f"❌ Scaler not found at: {SCALER_PATH}")
            return {"dl_score": 0.5}

        model = tf.keras.models.load_model(MODEL_PATH)
        print("✅ Model loaded successfully")

        # Verify input shape
        input_raw = np.array(sequence)
        print("Input raw shape:", input_raw.shape)

        if input_raw.shape != (5, 8):
            print(f"❌ Expected (5, 8); got {input_raw.shape} → using default 0.5")
            return {"dl_score": 0.5}

        # Reshape, scale, etc.
        seq_len, n_features = 5, 8
        input_flat         = input_raw.reshape(1, -1)
        scaler             = load(SCALER_PATH)
        input_scaled_flat  = scaler.transform(input_flat)
        input_scaled       = input_scaled_flat.reshape(1, seq_len, n_features)

        prediction = model.predict(input_scaled, verbose=0)
        print("Model prediction raw:", prediction)

        dl_score = float(prediction[0][0])
        print("✅ dl_score:", dl_score)
        return {"dl_score": dl_score}

    except Exception as e:
        print(f"❌ LSTM Error: {str(e)}")
        return {"dl_score": 0.5}


# ─────────────────────────────────────────────────────
# TEST BLOCK: run only when file is executed directly
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    sequence = [
        [0.2, 0.5, 0.1, 0.3, 0.9, 0.0, 0.8, 0.1],
        [0.3, 0.6, 0.2, 0.4, 0.8, 0.0, 0.7, 0.2],
        [0.4, 0.7, 0.3, 0.5, 0.7, 0.1, 0.6, 0.3],
        [0.5, 0.8, 0.4, 0.6, 0.6, 0.2, 0.5, 0.4],
        [0.6, 0.9, 0.5, 0.7, 0.5, 0.3, 0.4, 0.5],
    ]

    result = predict(sequence)
   