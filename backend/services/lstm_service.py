import os
import tensorflow as tf
import numpy as np

# Build a robust path relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'ml', 'model', 'lstm_model.h5')

def predict(sequence):
    try:
        # Check if file exists before trying to load
        if not os.path.exists(MODEL_PATH):
            print(f"❌ Model file not found at: {MODEL_PATH}")
            return {"dl_score": 0.5}
            
        model = tf.keras.models.load_model(MODEL_PATH)
        
        # Ensure sequence is a numpy array of shape (1, 5, 4)
        input_data = np.array(sequence).reshape(1, 5, 8)   
        prediction = model.predict(input_data, verbose=0)
        
        return {"dl_score": float(prediction[0][0])}
    except Exception as e:
        print(f"❌ LSTM Error: {str(e)}") # This will tell you the REAL problem
        return {"dl_score": 0.5}