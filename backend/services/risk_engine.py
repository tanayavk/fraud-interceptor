# backend/services/risk_engine.py
"""
Risk Engine — Core Brain
========================
Public surface:  assess(transaction: dict) -> dict

Pipeline:
  1. Sanitise & type-guard all inputs          (_sanitise)
  2. Hard short-circuit overrides              (BLOCK / ALLOW)
  3. Rule engine evaluation                    (rule_engine.evaluate)
  4. LSTM deep-learning score                  (lstm_service.predict)
  5. Weighted fusion & action decision
  6. Persist to history

Feature order fed to LSTM (must match scaler / model training):
  [Amount, Hour, Z-Score, Frequency, Device, Location, Category, Age]
"""

import time
from datetime import datetime

from backend.config import (
    RULE_WEIGHT,
    DL_WEIGHT,
    SEQUENCE_LENGTH,
    BLOCK_THRESHOLD,
    VERIFY_THRESHOLD,
    ENABLE_LOGGING,
)
import backend.services.rule_engine as _rule_mod
import backend.services.lstm_service as _lstm_mod
from backend.services.sequence_builder import build_sequence
from backend.db.database import get_history, append_transaction


# ── Logging helper ────────────────────────────────────────────────────────────

def _log(*args) -> None:
    if ENABLE_LOGGING:
        print("[FraudInterceptor]", *args)


# ── Input sanitisation ────────────────────────────────────────────────────────

def _sanitise(transaction: dict) -> dict:
    """
    Returns a clean, fully-typed copy of *transaction*.

    Every field that downstream modules touch is explicitly cast here so
    that None / missing values never propagate into NumPy / Keras.

    Field defaults:
        amount              → 0.0
        user_id             → "demo_user"
        recipient           → ""
        timestamp           → current epoch
        hour                → 12  (noon fallback)
        amount_zscore       → 0.0 (recomputed from history when available)
        tx_frequency_60m    → 1.0
        device_fingerprint  → 1.0
        location_consistency→ 1
        category_risk       → 0.1
        account_age_days    → 365
    """
    tx = dict(transaction)

    # ── Core identity fields ──────────────────────────────────────────────────
    tx["user_id"]   = str(tx.get("user_id") or "demo_user").strip() or "demo_user"
    tx["recipient"] = str(tx.get("recipient") or "").strip()

    # ── Amount — must be a non-negative float ─────────────────────────────────
    try:
        tx["amount"] = float(tx.get("amount") or 0.0)
    except (TypeError, ValueError):
        tx["amount"] = 0.0

    # ── Timestamp & Hour ──────────────────────────────────────────────────────
    raw_ts = tx.get("timestamp")
    try:
        ts = float(raw_ts) if raw_ts is not None else time.time()
    except (TypeError, ValueError):
        ts = time.time()

    tx["timestamp"] = ts

    try:
        tx["hour"] = int(datetime.fromtimestamp(ts).hour)
    except (OSError, OverflowError, ValueError):
        tx["hour"] = 12   # safe noon fallback

    # ── LSTM scalar features — explicit float/int casts ───────────────────────
    def _f(key: str, default: float) -> float:
        val = tx.get(key)
        try:
            return float(val) if val is not None else default
        except (TypeError, ValueError):
            return default

    def _i(key: str, default: int) -> int:
        val = tx.get(key)
        try:
            return int(float(val)) if val is not None else default
        except (TypeError, ValueError):
            return default

    tx["tx_frequency_60m"]     = _f("tx_frequency_60m",     1.0)
    tx["device_fingerprint"]   = _f("device_fingerprint",   1.0)
    tx["location_consistency"] = _i("location_consistency", 1)
    tx["category_risk"]        = _f("category_risk",        0.1)
    tx["account_age_days"]     = 365   # static demo value

    # ── amount_zscore — recomputed from history; safe against zero division ───
    try:
        history = get_history(tx["user_id"])
        if history:
            amounts = [float(h.get("amount") or 0.0) for h in history if isinstance(h, dict)]
            if amounts:
                avg = sum(amounts) / len(amounts)
                # Avoid division by zero: fall back to 0.0 when avg ≈ 0
                denom = avg if avg > 0.0 else 1.0
                tx["amount_zscore"] = (tx["amount"] - avg) / denom
            else:
                tx["amount_zscore"] = 0.0
        else:
            tx["amount_zscore"] = 0.0
    except Exception as exc:
        _log(f"amount_zscore computation failed — defaulting to 0.0: {exc}")
        tx["amount_zscore"] = 0.0

    return tx


# ── Public entry point ────────────────────────────────────────────────────────

def assess(transaction: dict) -> dict:
    """
    Full fraud-risk assessment for a single transaction.

    Args:
        transaction: {user_id, amount, recipient, [timestamp], …}

    Returns:
        {risk_score: float, action: str, reasons: list[str]}
    """
    # ── Step 1: Sanitise ──────────────────────────────────────────────────────
    try:
        tx = _sanitise(transaction)
    except Exception as exc:
        _log(f"_sanitise() raised unexpectedly — using raw input: {exc}")
        tx = dict(transaction)
        tx.setdefault("user_id",    "demo_user")
        tx.setdefault("amount",     0.0)
        tx.setdefault("hour",       12)
        tx.setdefault("amount_zscore",       0.0)
        tx.setdefault("tx_frequency_60m",    1.0)
        tx.setdefault("device_fingerprint",  1.0)
        tx.setdefault("location_consistency", 1)
        tx.setdefault("category_risk",       0.1)
        tx.setdefault("account_age_days",    365)

    amount  = float(tx.get("amount") or 0.0)
    user_id = str(tx.get("user_id") or "demo_user")

    _log(f"--- Assessing | user={user_id} | amount={amount} | recipient={tx.get('recipient')} ---")

    # ── Step 2a: Hard BLOCK — high-value short-circuit ────────────────────────
    # Bypass all AI/rule layers. Immediate deterministic block.
    if amount >= 150_000:
        _log("Nuclear BLOCK — amount >= 150,000")
        return {
            "risk_score": 1.0,
            "action":     "BLOCK",
            "reasons":    ["CRITICAL: Transaction exceeds authorised limit (Demo Block)"],
        }

    # ── Step 2b: Hard ALLOW — micro-transaction short-circuit ─────────────────
    # Persist so the LSTM accumulates a "normal behaviour" baseline.
    if amount < 500:
        _log("Nuclear ALLOW — amount < 500")
        try:
            append_transaction(user_id, tx)
        except Exception as exc:
            _log(f"DB write failed (ALLOW path): {exc}")
        return {
            "risk_score": 0.05,
            "action":     "ALLOW",
            "reasons":    ["Trusted small-value transaction"],
        }

    # ── Step 3: Fetch history (after sanitise to avoid double-read) ───────────
    try:
        history = get_history(user_id)
    except Exception as exc:
        _log(f"DB read failed — empty history used: {exc}")
        history = []

    # ── Step 4: Rule Engine ───────────────────────────────────────────────────
    rule_score = 0.0
    flags      = []
    try:
        rule_res   = _rule_mod.evaluate(tx, history)
        rule_score = float(rule_res.get("rule_score") or 0.0)
        rule_score = max(0.0, min(1.0, rule_score))
        flags      = rule_res.get("flags", []) or []
    except Exception as exc:
        _log(f"rule_engine.evaluate() failed — rule_score=0.0: {exc}")

    _log(f"Rule score : {rule_score:.4f} | Flags: {flags or 'none'}")

    # ── Step 5: LSTM Deep-Learning Score ─────────────────────────────────────
    # DL_BASELINE: LSTM models trained on imbalanced datasets often output a
    # high raw score even for clean transactions.  We subtract a calibrated
    # baseline so the model's *relative* deviation drives the score, not its
    # absolute output.  Clamp the result to [0, 1].
    DL_BASELINE = 0.55   # tune downward if model is over-predicting on clean data
    dl_score_raw = 0.5
    dl_score     = 0.5   # conservative fallback
    try:
        sequence     = build_sequence(tx, history, max_len=SEQUENCE_LENGTH)
        dl_res       = _lstm_mod.predict(sequence)
        dl_score_raw = float(dl_res.get("dl_score") or 0.5)
        # Calibrate: subtract baseline, re-scale to [0, 1]
        dl_score = max(0.0, min(1.0, (dl_score_raw - DL_BASELINE) / (1.0 - DL_BASELINE)))
    except Exception as exc:
        _log(f"lstm_service.predict() failed — dl_score=0.5 fallback: {exc}")

    _log(f"DL score   : raw={dl_score_raw:.4f} → calibrated={dl_score:.4f}")

    # ── Step 6: Adaptive Weighted Fusion ─────────────────────────────────────
    # Standard formula: RULE_WEIGHT * rule_score + DL_WEIGHT * dl_score
    # Problem: if rule_score is 0.0, DL contribution is capped at 0.4×1.0 = 0.4,
    # which is below VERIFY_THRESHOLD (0.55) — DL is permanently silenced.
    #
    # Fix: when rules are silent (rule_score == 0.0), give DL full weight so
    # a highly anomalous LSTM output alone can still trigger VERIFY or BLOCK.
    if rule_score == 0.0:
        # Rules found nothing — let the LSTM speak for itself
        final_score = round(dl_score, 4)
        _log(f"Final score: {final_score}  (rules silent → DL-only: {dl_score:.4f})")
    else:
        # Normal weighted fusion
        final_score = round(RULE_WEIGHT * rule_score + DL_WEIGHT * dl_score, 4)
        _log(f"Final score: {final_score}  ({RULE_WEIGHT}×{rule_score} + {DL_WEIGHT}×{dl_score})")

    # ── Step 7: Action decision ───────────────────────────────────────────────
    if final_score >= BLOCK_THRESHOLD:
        action = "BLOCK"
    elif final_score >= VERIFY_THRESHOLD:
        action = "VERIFY"
    else:
        action = "ALLOW"

    _log(f"Action     : {action}  (BLOCK>={BLOCK_THRESHOLD}, VERIFY>={VERIFY_THRESHOLD})")

    # ── Step 8: Persist ───────────────────────────────────────────────────────
    try:
        append_transaction(user_id, tx)
    except Exception as exc:
        _log(f"DB write failed: {exc}")

    return {
        "risk_score": final_score,
        "action":     action,
        "reasons":    flags if flags else [],
    }