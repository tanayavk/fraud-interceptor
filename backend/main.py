"""
Fraud Interceptor — Backend Entry Point
==========================================
Run with:
    uvicorn backend.main:app --reload --port 8000
"""

# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.risk import router as risk_router

app = FastAPI(title="Fraud Interceptor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(risk_router)


@app.get("/health")
def health():
    return {"status": "ok", "message": "Fraud Interceptor is running"}