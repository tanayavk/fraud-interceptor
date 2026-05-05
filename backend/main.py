from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.risk_engine import calculate_final_risk
from services.sequence_builder import get_user_sequence

app = FastAPI(title="Fraud Interceptor 2026")

# 1. Define the Input Schema (Matching your 8-parameter plan)
class TransactionRequest(BaseModel):
    user_id: str
    amount_inr: float
    hour: int
    geo_distance: float
    merchant_risk: float
    # These are used for Cyber Rules specifically
    device_id: str
    location_city: str

@app.post("/analyze-transaction")
async def analyze(request: TransactionRequest):
    try:
        # A. Fetch History: Get the last 4 transactions + current one to make 5
        # The sequence_builder handles the SQL query and padding
        user_history = get_user_sequence(request.user_id, window_size=5)
        
        # B. Prepare Current Data: Format for the Rule Engine
        current_txn = {
            "amount": request.amount_inr,
            "hour": request.hour,
            "distance": request.geo_distance,
            "merchant_risk": request.merchant_risk,
            "device_id": request.device_id
        }

        # C. Run Hybrid Analysis: This calls Rules + LSTM
        # risk_engine.py returns scores and the decision (BLOCK/APPROVE)
        result = calculate_final_risk(current_txn, user_history)

        return {
            "status": "success",
            "user_id": request.user_id,
            "analysis": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)