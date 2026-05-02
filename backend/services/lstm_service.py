# backend/services/lstm_service.py
"""
LSTM Service - Deep Learning Layer
CONTRACT: predict(sequence) -> {"dl_score": float}
STATUS: Dummy placeholder - returns 0.5.
TEAMMATE (ML): Replace the body of predict() with real model inference.
DO NOT rename the function. DO NOT change return keys.
"""


def predict(sequence) -> dict:
    """
    Args:
        sequence : numpy array of shape (1, 5, 4) from sequence_builder,
                   OR None / empty (must be handled gracefully)

    Returns:
        {"dl_score": float [0.0-1.0]}
        0.0 = normal behaviour, 1.0 = highly anomalous
    """
    # Fallback: no sequence available
    if sequence is None:
        return {"dl_score": 0.5}

    try:
        import numpy as np
        if isinstance(sequence, np.ndarray) and sequence.size == 0:
            return {"dl_score": 0.5}
    except ImportError:
        pass

    if hasattr(sequence, "__len__") and len(sequence) == 0:
        return {"dl_score": 0.5}

    # ----------------------------------------------------------------
    # DUMMY — replace with real LSTM inference e.g.:
    # ----------------------------------------------------------------
    # import numpy as np
    # from tensorflow import keras
    # model = keras.models.load_model("ml/lstm_model.h5")
    # score = float(model.predict(sequence)[0][0])
    # return {"dl_score": score}

    return {"dl_score": 0.5}