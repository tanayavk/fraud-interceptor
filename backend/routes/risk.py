# # backend/routes/risk.py
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel, Field
# from backend.services.risk_engine import assess

# router = APIRouter()


# class TransactionRequest(BaseModel):
#     user_id:   str   = Field(..., example="user_123")
#     amount:    float = Field(..., gt=0, example=5000.0)
#     recipient: str   = Field(..., example="abc@upi")


# class RiskResponse(BaseModel):
#     risk_score: float
#     action:     str
#     reasons:    list


# @router.post("/risk", response_model=RiskResponse)
# def evaluate_risk(payload: TransactionRequest):
#     try:
#         result = assess(payload.model_dump())
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc))
#     return RiskResponse(**result)

# backend/routes/risk.py
"""
POST /risk — Transaction risk assessment endpoint.
Validates input, delegates to risk_engine, returns strict API format.
Never crashes — all errors return a safe VERIFY response.
"""
import time
from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from backend.services.risk_engine import assess

router = APIRouter()


# ── Request schema ───────────────────────────────────────────────────────
class TransactionRequest(BaseModel):
    user_id   : str   = Field(default="anonymous", description="User identifier")
    amount    : float = Field(..., gt=0, le=10_000_000, description="Amount in INR, must be > 0")
    recipient : str   = Field(..., min_length=1, description="Recipient UPI ID")
    timestamp : float = Field(default=None, description="Unix timestamp (auto-filled if missing)")
    device_id : str = Field(default="unknown", description="Device identifier (optional)")
    
    @field_validator("user_id")
    @classmethod
    def clean_user_id(cls, v):
        v = str(v).strip()
        return v if v else "anonymous"

    @field_validator("recipient")
    @classmethod
    def clean_recipient(cls, v):
        return str(v).strip()

    @field_validator("timestamp", mode="before")
    @classmethod
    def default_timestamp(cls, v):
        # If client didn't send a timestamp, inject current server time
        if v is None or v == 0:
            return time.time()
        return float(v)
    
    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, v):
        try:
            return float(v)
        except (TypeError, ValueError):
            raise ValueError("amount must be a number")


# ── Response schema ──────────────────────────────────────────────────────
class RiskResponse(BaseModel):
    risk_score : float
    action     : str    # "ALLOW" | "VERIFY" | "BLOCK"
    reasons    : list


# ── Endpoint ─────────────────────────────────────────────────────────────
@router.post("/risk", response_model=RiskResponse)
def evaluate_risk(payload: TransactionRequest) -> RiskResponse:
    """
    Accepts a transaction and returns a fraud risk assessment.
    All business logic lives in risk_engine.assess() — not here.
    """
    try:
        result = assess(payload.model_dump())
    except Exception as exc:
        # Absolute last-resort fallback — should never happen after
        # risk_engine's own try/except, but just in case.
        print(f"[ROUTE] Unexpected error in assess(): {exc}")
        result = {
            "risk_score": 0.5,
            "action":     "VERIFY",
            "reasons":    ["Risk assessment temporarily unavailable. Please verify manually."],
        }

    # Validate the response has the required shape before returning
    return RiskResponse(
        risk_score = float(result.get("risk_score", 0.5)),
        action     = str(result.get("action", "VERIFY")),
        reasons    = list(result.get("reasons", [])),
    )