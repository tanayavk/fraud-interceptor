import numpy as np
import joblib
import tensorflow as tf
import shap

# Load model and scaler
MODEL_PATH = 'ml/model/lstm_model.h5'
SCALER_PATH = 'ml/model/scaler.pkl'

def get_transaction_explanation(sequence):
    """
    Explains why the LSTM gave a specific dl_score.
    Returns the top contributing features.
    """
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        
        # Prepare input (Same logic as lstm_service)
        seq_array = np.array(sequence, dtype=np.float32)
        if seq_array.shape[0] < 5:
            padding = np.zeros((5 - seq_array.shape[0], 4))
            seq_array = np.vstack((padding, seq_array))
        else:
            seq_array = seq_array[-5:]
            
        input_data = np.expand_dims(seq_array, axis=0)

        # We use a simple GradientExplainer for Deep Learning models
        # Note: In a real demo, you'd use a small background dataset for SHAP
        explainer = shap.GradientExplainer(model, np.zeros((1, 5, 4)))
        shap_values = explainer.shap_values(input_data)

        # Aggregate SHAP values across the sequence for each feature
        # Features: [Amount_INR, Hour, Geo_Distance_km, Merchant_Risk_Score]
        feature_importance = np.abs(shap_values[0]).mean(axis=0).flatten()
        
        feature_names = ['Amount', 'Hour', 'Distance', 'Merchant Risk']
        explanation_map = dict(zip(feature_names, feature_importance))
        
        # Sort to find the "Top Offender"
        sorted_explanation = sorted(explanation_map.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "primary_factor": sorted_explanation[0][0],
            "impact_scores": {k: float(v) for k, v in sorted_explanation}
        }

    except Exception as e:
        print(f"Explanation Error: {e}")
        return {"primary_factor": "Unknown", "impact_scores": {}}