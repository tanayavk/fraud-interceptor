# # backend/services/lstm_service.py
# """
# LSTM Service - Deep Learning Layer
# CONTRACT: predict(sequence) -> {"dl_score": float}
# STATUS: Dummy placeholder - returns 0.5.
# TEAMMATE (ML): Replace the body of predict() with real model inference.
# DO NOT rename the function. DO NOT change return keys.
# """


# def predict(sequence) -> dict:
#     """
#     Args:
#         sequence : numpy array of shape (1, 5, 4) from sequence_builder,
#                    OR None / empty (must be handled gracefully)

#     Returns:
#         {"dl_score": float [0.0-1.0]}
#         0.0 = normal behaviour, 1.0 = highly anomalous
#     """
#     # Fallback: no sequence available
#     if sequence is None:
#         return {"dl_score": 0.5}

#     try:
#         import numpy as np
#         if isinstance(sequence, np.ndarray) and sequence.size == 0:
#             return {"dl_score": 0.5}
#     except ImportError:
#         pass

#     if hasattr(sequence, "__len__") and len(sequence) == 0:
#         return {"dl_score": 0.5}

#     # ----------------------------------------------------------------
#     # DUMMY — replace with real LSTM inference e.g.:
#     # ----------------------------------------------------------------
#     # import numpy as np
#     # from tensorflow import keras
#     # model = keras.models.load_model("ml/lstm_model.h5")
#     # score = float(model.predict(sequence)[0][0])
#     # return {"dl_score": score}

#     return {"dl_score": 0.5}

import os
import keras # Use keras directly instead of tf.keras for Keras 3 models
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'backend', 'models', 'lstm_model.h5')

_MODEL = None

try:
    if os.path.exists(MODEL_PATH):
        # Keras 3 loader is smarter about metadata like 'quantization_config'
        _MODEL = keras.models.load_model(MODEL_PATH)
        print("✅ LSTM Model loaded successfully using Keras 3")
    else:
        print(f"⚠️ Model file missing at {MODEL_PATH}")
except Exception as e:
    print(f"❌ Load Error: {e}")
    # Final fallback: Try loading without compiling if there's still a metadata mismatch
    try:
        _MODEL = keras.models.load_model(MODEL_PATH, compile=False)
        print("✅ LSTM Model loaded (Bypass Mode)")
    except:
        print("🚨 Critical: Model could not be loaded even with bypass.")

def predict(sequence):
    if _MODEL is None:
        return {"dl_score": 0.5}
    
    try:
        # Keras 3 expects numpy arrays
        input_data = np.array(sequence).reshape(1, 5, 8).astype('float32')
        prediction = _MODEL.predict(input_data, verbose=0)
        return {"dl_score": float(prediction[0][0])}
    except Exception as e:
        print(f"❌ Prediction Error: {e}")
        return {"dl_score": 0.5}