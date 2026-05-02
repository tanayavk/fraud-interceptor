# backend/routes/risk.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.services.risk_engine import assess

router = APIRouter()


class TransactionRequest(BaseModel):
    user_id:   str   = Field(..., example="user_123")
    amount:    float = Field(..., gt=0, example=5000.0)
    recipient: str   = Field(..., example="abc@upi")


class RiskResponse(BaseModel):
    risk_score: float
    action:     str
    reasons:    list


@router.post("/risk", response_model=RiskResponse)
def evaluate_risk(payload: TransactionRequest):
    try:
        result = assess(payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return RiskResponse(**result)