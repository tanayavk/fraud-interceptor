from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import schema
import database
from services.risk_engine import calculate_final_risk
from services.sequence_builder import get_user_sequence
from backend.db.database import init_db
init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db() # Create table on startup
    yield

app = FastAPI(title="Fraud Interceptor 2026", lifespan=lifespan)

@app.post("/analyze-transaction", response_model=schema.TransactionResponse)
async def analyze(request: schema.TransactionBase):
    try:
        # Fetch history for the LSTM sequence
        user_history = get_user_sequence(request.user_id, window_size=5)
        
        current_txn = {
            "amount": request.amount_inr,
            "hour": request.hour,
            "distance": request.geo_distance,
            "merchant_risk": request.merchant_risk,
            "device_id": request.device_id,
            "location": request.location_city
        }

        # Hybrid Analysis: 40% Rules, 60% LSTM
        result = calculate_final_risk(current_txn, user_history)

        return {
            "status": "success",
            "risk_score": result['final_risk_score'],
            "decision": result['decision']
        }
    except Exception as e:
        print(f"Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal analysis failure")