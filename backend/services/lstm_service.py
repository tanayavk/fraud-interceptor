import numpy as np
import tensorflow as tf
import os

# Failsafe: Load model globally
MODEL_PATH = 'ml/model/lstm_model.h5'
model = None

if os.path.exists(MODEL_PATH):
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
    except:
        model = None

def predict(sequence):
    """
    Input: List of lists [[amt, hr, dev, vel], ...]
    Output: {"dl_score": float}
    """
    # FAILSAFE: Data missing, empty sequence, or model load failure
    if not sequence or model is None or len(sequence) == 0:
        return {"dl_score": 0.5}

    try:
        # Convert to numpy and reshape to (1, N, 4)
        seq_array = np.array(sequence, dtype=np.float32)
        
        # Ensure sequence length matches model training (padding/truncating)
        if seq_array.shape[0] < 5:
            # Pad with zeros if sequence is too short
            padding = np.zeros((5 - seq_array.shape[0], 4))
            seq_array = np.vstack((padding, seq_array))
        else:
            seq_array = seq_array[-5:] # Take last 5
            
        input_data = np.expand_dims(seq_array, axis=0)
        
        # Inference
        prediction = model.predict(input_data, verbose=0)
        score = float(prediction[0][0])
        
        return {"dl_score": round(score, 4)}

    except Exception as e:
        # FAILSAFE: Any execution error
        print(f"DL Error: {e}")
        return {"dl_score": 0.5}