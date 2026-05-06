from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
import schema
import database
from services.risk_engine import calculate_final_risk
from services.sequence_builder import get_user_sequence

# 1. Lifespan: Ensures the DB table is created before the app starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield

app = FastAPI(
    title="Fraud Interceptor 2026",
    description="LSTM-based Financial Fraud Detection System",
    lifespan=lifespan
)

@app.post("/analyze-transaction", response_model=schema.TransactionResponse)
async def analyze(request: schema.TransactionBase):
    """
    Main endpoint that processes 8 parameters to determine fraud risk.
    """
    try:
        # A. Fetch Transaction History (The Sequence)
        # Pulls from transactions.db via sequence_builder
        user_history = get_user_sequence(request.user_id, window_size=5)
        
        # B. Current Transaction Data (Extracted from the validated Request)
        current_txn = {
            "amount": request.amount_inr,
            "hour": request.hour,
            "distance": request.geo_distance,
            "merchant_risk": request.merchant_risk,
            "device_id": request.device_id,
            "location": request.location_city
        }

        # C. Run Hybrid Analysis (Rule Engine + LSTM Service)
        # Weights: 40% Rules, 60% Deep Learning
        result = calculate_final_risk(current_txn, user_history)

        # D. Return standardized response
        return {
            "status": "success",
            "risk_score": result['final_risk_score'],
            "decision": result['decision']
        }

    except Exception as e:
        # Log the error for debugging
        print(f"Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal analysis failure")

if __name__ == "__main__":
    import uvicorn
    # Host 0.0.0.0 allows access from other devices in your network for the demo
    uvicorn.run(app, host="0.0.0.0", port=8000)