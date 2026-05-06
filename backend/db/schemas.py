from pydantic import BaseModel

class TransactionBase(BaseModel):
    user_id: str
    amount_inr: float
    hour: int
    geo_distance: float
    merchant_risk: float
    device_id: str
    location_city: str

class TransactionResponse(BaseModel):
    status: str
    risk_score: float
    decision: str