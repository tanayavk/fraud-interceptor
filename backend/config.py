# backend/config.py
"""
Centralised configuration — change thresholds here only.
No other file should hardcode these values.
"""

# ── Decision Thresholds ────────────────────────────────────────────────────
BLOCK_THRESHOLD  = 0.75   # risk_score >= this  → BLOCK
VERIFY_THRESHOLD = 0.55  # risk_score >= this  → VERIFY  (else ALLOW)

# ── Score Weights (must sum to 1.0) ───────────────────────────────────────
RULE_WEIGHT = 0.6
DL_WEIGHT   = 0.4

# ── Safe fallback scores (used when a module crashes) ─────────────────────
RULE_FALLBACK_SCORE = 0.0  # If rules fail, assume safe
DL_FALLBACK_SCORE   = 0.3  # If AI fails, assume slightly suspicious but below Verify

# ── History window ─────────────────────────────────────────────────────────
MAX_HISTORY = 5   # transactions to keep per user

# ── Logging ────────────────────────────────────────────────────────────────
ENABLE_LOGGING = True

SEQUENCE_LENGTH = 5  # number of past transactions fed to LSTM