# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routes.risk import router as risk_router
from backend.config import BLOCK_THRESHOLD, VERIFY_THRESHOLD

app = FastAPI(
    title       = "Fraud Interceptor API",
    description = "Real-time client-side fraud prevention.",
    version     = "2.0.0",
)

app.mount("/bank", StaticFiles(directory="mock-bank", html=True), name="bank")

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["GET", "POST"],
    allow_headers  = ["*"],
)

app.include_router(risk_router)


@app.get("/health")
def health():
    return {
        "status"           : "ok",
        "message"          : "Fraud Interceptor is running",
        "block_threshold"  : BLOCK_THRESHOLD,
        "verify_threshold" : VERIFY_THRESHOLD,
    }


@app.on_event("startup")
def on_startup():
    print("=" * 50)
    print("  Fraud Interceptor Backend  v2.0")
    print(f"  BLOCK  threshold : {BLOCK_THRESHOLD}")
    print(f"  VERIFY threshold : {VERIFY_THRESHOLD}")
    print("  Listening on     : http://127.0.0.1:8000")
    print("=" * 50)