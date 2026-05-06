# backend/services/risk_engine.py
"""
Risk Engine — Core Brain
========================
Full pipeline with:
  ✓ Configurable thresholds (from config.py)
  ✓ Per-module try/except fallback (never crashes)
  ✓ Structured logging (rule_score, dl_score, final_score)
  ✓ Input sanitisation before passing to modules
  ✓ Timestamp injection if missing
"""
import time
import traceback

from backend.config import (
    BLOCK_THRESHOLD, SEQUENCE_LENGTH, VERIFY_THRESHOLD,
    RULE_WEIGHT, DL_WEIGHT,
    RULE_FALLBACK_SCORE, DL_FALLBACK_SCORE,
    ENABLE_LOGGING,
)
import backend.services.rule_engine      as _rule_mod
import backend.services.lstm_service     as _lstm_mod
from backend.services.sequence_builder import build_sequence as build_lstm_sequence
from backend.services.explanation      import build_reasons
from backend.db.database               import get_history, append_transaction


# ── Logging helper ───────────────────────────────────────────────────────
def _log(*args):
    if ENABLE_LOGGING:
        print("[FraudInterceptor]", *args)


# ── Sanitise incoming transaction ────────────────────────────────────────
def _sanitise(transaction: dict) -> dict:
    """Ensure required fields exist with sane defaults."""
    tx = dict(transaction)  # don't mutate original
    tx["user_id"]   = str(tx.get("user_id", "unknown")).strip() or "unknown"
    tx["amount"]    = float(tx.get("amount", 0) or 0)
    tx["recipient"] = str(tx.get("recipient", "")).strip()
    if "timestamp" not in tx or not tx["timestamp"]:
        tx["timestamp"] = time.time()
    return tx


# ── Action decision ──────────────────────────────────────────────────────
def _decide_action(score: float) -> str:
    if score >= BLOCK_THRESHOLD:
        return "BLOCK"
    if score >= VERIFY_THRESHOLD:
        return "VERIFY"
    return "ALLOW"


# ════════════════════════════════════════════════════════════════════════
#  assess() — the only public function; called by the route
# ════════════════════════════════════════════════════════════════════════

def assess(transaction: dict) -> dict:
    """
    Full fraud risk assessment for a single transaction.

    Args:
        transaction: {"user_id": str, "amount": float, "recipient": str}

    Returns:
        {"risk_score": float, "action": str, "reasons": list[str]}
    """
    # ── Step 1: Sanitise input ───────────────────────────────────────
    try:
        tx = _sanitise(transaction)
    except Exception:
        _log("Sanitisation failed — using raw input")
        tx = transaction

    user_id = tx.get("user_id", "unknown")
    _log(f"--- Assessing | user={user_id} | amount={tx.get('amount')} | recipient={tx.get('recipient')} ---")

    # ── Step 2: Fetch history ────────────────────────────────────────
    try:
        history = get_history(user_id)
    except Exception:
        _log("DB read failed — using empty history")
        history = []

    # ── Step 3: Rule Engine (with fallback) ──────────────────────────
    rule_score = RULE_FALLBACK_SCORE
    flags      = []
    try:
        rule_result = _rule_mod.evaluate(tx, history)
        rule_score  = float(rule_result.get("rule_score", RULE_FALLBACK_SCORE))
        flags       = rule_result.get("flags", [])
        rule_score = max(0.0, min(1.0, rule_score))
    except Exception as e:
        _log(f"rule_engine failed (fallback={RULE_FALLBACK_SCORE}): {e}")

    _log(f"Rule score : {rule_score} | Flags: {flags or 'none'}")

    # ── Step 4: LSTM (with fallback) ─────────────────────────────────
    dl_score = DL_FALLBACK_SCORE
    try:
        sequence  = build_lstm_sequence(tx, history, max_len=SEQUENCE_LENGTH)
        dl_result = _lstm_mod.predict(sequence)
        dl_score  = float(dl_result.get("dl_score", DL_FALLBACK_SCORE))
        dl_score  = max(0.0, min(1.0, dl_score))
    except Exception as e:
        _log(f"lstm_service failed (fallback={DL_FALLBACK_SCORE}): {e}")

    _log(f"DL score   : {dl_score}")

    # ── Step 5: Combine scores ───────────────────────────────────────
    final_score = round(RULE_WEIGHT * rule_score + DL_WEIGHT * dl_score, 4)
    _log(f"Final score: {final_score}  ({RULE_WEIGHT}×{rule_score} + {DL_WEIGHT}×{dl_score})")

    # ── Step 6: Decide action ────────────────────────────────────────
    action = _decide_action(final_score)
    _log(f"Action     : {action}  (BLOCK≥{BLOCK_THRESHOLD}, VERIFY≥{VERIFY_THRESHOLD})")

    # ── Step 7: Build explanation ────────────────────────────────────
    try:
        reasons = build_reasons(flags, dl_score, action)
    except Exception as e:
        self._log(f"Explanation failed: {e}")
        # Fallback only if the engine actually crashes
        reasons = ["Please verify this transaction before proceeding."]

    # ── Step 8: Save to history ──────────────────────────────────────
    try:
        append_transaction(user_id, tx)
    except Exception as e:
        _log(f"DB write failed: {e}")

    _log(f"Response   : risk_score={final_score}, action={action}, reasons={len(reasons)} items")
    _log("---")

    return {
        "risk_score": final_score,
        "action":     action,
        "reasons":    reasons,
    }