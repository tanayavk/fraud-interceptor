from fastapi import APIRouter

router = APIRouter()

@router.post("/risk")
def get_risk(data: dict):
    return {
        "risk_score": 0.8,
        "risk_level": "HIGH",
        "action": "BLOCK",
        "reasons": ["Dummy test reason"]
    }