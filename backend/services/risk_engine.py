# # backend/services/risk_engine.py
# """
# Risk Engine — Core Brain
# ========================
# Full pipeline with:
#   ✓ Configurable thresholds (from config.py)
#   ✓ Per-module try/except fallback (never crashes)
#   ✓ Structured logging (rule_score, dl_score, final_score)
#   ✓ Input sanitisation before passing to modules
#   ✓ Timestamp injection if missing
# """
# import time
# from datetime import datetime
# import traceback

# from backend.config import (
#     BLOCK_THRESHOLD, SEQUENCE_LENGTH, VERIFY_THRESHOLD,
#     RULE_WEIGHT, DL_WEIGHT,
#     RULE_FALLBACK_SCORE, DL_FALLBACK_SCORE,
#     ENABLE_LOGGING,
# )
# import backend.services.rule_engine      as _rule_mod
# import backend.services.lstm_service     as _lstm_mod
# from backend.services.sequence_builder import build_sequence as build_lstm_sequence
# from backend.services.explanation      import build_reasons
# from backend.db.database               import get_history, append_transaction


# # ── Logging helper ───────────────────────────────────────────────────────
# def _log(*args):
#     if ENABLE_LOGGING:
#         print("[FraudInterceptor]", *args)


# # ── Sanitise incoming transaction ────────────────────────────────────────
# def _sanitise(transaction: dict) -> dict:
#     tx = dict(transaction)
#     tx["user_id"] = str(tx.get("user_id", "unknown")).strip() or "unknown"
#     tx["amount"] = float(tx.get("amount", 0))
    
#     # Inject DL features
#     ts = tx.get("timestamp", time.time())
#     tx["timestamp"] = ts
#     tx["hour"] = datetime.fromtimestamp(ts).hour
    
#     # Fallbacks for remaining features
#     tx["amount_deviation"] = 0.0 
#     tx["frequency"] = 1.0
#     tx["device_fingerprint"] = tx.get("device_id", 1) # Map device_id to int if possible
#     tx["location_consistency"] = 1
#     tx["category_risk"] = 0.1
#     tx["account_age"] = 365 # Per your preference: static 365
#     return tx


# # ── Action decision ──────────────────────────────────────────────────────
# def _decide_action(score: float) -> str:
#     if score >= BLOCK_THRESHOLD:
#         return "BLOCK"
#     if score >= VERIFY_THRESHOLD:
#         return "VERIFY"
#     return "ALLOW"


# # ════════════════════════════════════════════════════════════════════════
# #  assess() — the only public function; called by the route
# # ════════════════════════════════════════════════════════════════════════

# # def assess(transaction: dict) -> dict:
# #     """
# #     Full fraud risk assessment for a single transaction.

# #     Args:
# #         transaction: {"user_id": str, "amount": float, "recipient": str}

# #     Returns:
# #         {"risk_score": float, "action": str, "reasons": list[str]}
# #     """
# #     # ── Step 1: Sanitise input ───────────────────────────────────────
# #     try:
# #         tx = _sanitise(transaction)
# #     except Exception:
# #         _log("Sanitisation failed — using raw input")
# #         tx = transaction

# #     user_id = tx.get("user_id", "unknown")
# #     _log(f"--- Assessing | user={user_id} | amount={tx.get('amount')} | recipient={tx.get('recipient')} ---")

# #     # ── Step 2: Fetch history ────────────────────────────────────────
# #     try:
# #         history = get_history(user_id)
# #     except Exception:
# #         _log("DB read failed — using empty history")
# #         history = []

# #     # ── Step 3: Rule Engine (with fallback) ──────────────────────────
# #     rule_score = RULE_FALLBACK_SCORE
# #     flags      = []
# #     try:
# #         rule_result = _rule_mod.evaluate(tx, history)
# #         rule_score  = float(rule_result.get("rule_score", RULE_FALLBACK_SCORE))
# #         flags       = rule_result.get("flags", [])
# #         rule_score = max(0.0, min(1.0, rule_score))
# #     except Exception as e:
# #         _log(f"rule_engine failed (fallback={RULE_FALLBACK_SCORE}): {e}")

# #     _log(f"Rule score : {rule_score} | Flags: {flags or 'none'}")

# #     # ── Step 4: LSTM (with fallback) ─────────────────────────────────
# #     dl_score = DL_FALLBACK_SCORE
# #     try:
# #         sequence  = build_lstm_sequence(tx, history, max_len=SEQUENCE_LENGTH)
# #         dl_result = _lstm_mod.predict(sequence)
# #         dl_score  = float(dl_result.get("dl_score", DL_FALLBACK_SCORE))
# #         dl_score  = max(0.0, min(1.0, dl_score))
# #     except Exception as e:
# #         _log(f"lstm_service failed (fallback={DL_FALLBACK_SCORE}): {e}")

# #     _log(f"DL score   : {dl_score}")

# #     # ── Step 5: Combine scores ───────────────────────────────────────
# #     final_score = round(RULE_WEIGHT * rule_score + DL_WEIGHT * dl_score, 4)
# #     _log(f"Final score: {final_score}  ({RULE_WEIGHT}×{rule_score} + {DL_WEIGHT}×{dl_score})")

# #     # ── Step 6: Decide action ────────────────────────────────────────
# #     action = _decide_action(final_score)
# #     _log(f"Action     : {action}  (BLOCK≥{BLOCK_THRESHOLD}, VERIFY≥{VERIFY_THRESHOLD})")

# #     # ── Step 7: Build explanation ────────────────────────────────────
# #     try:
# #         reasons = build_reasons(flags, dl_score, action)
# #     except Exception as e:
# #         self._log(f"Explanation failed: {e}")
# #         # Fallback only if the engine actually crashes
# #         reasons = ["Please verify this transaction before proceeding."]

# #     # ── Step 8: Save to history ──────────────────────────────────────
# #     try:
# #         append_transaction(user_id, tx)
# #     except Exception as e:
# #         _log(f"DB write failed: {e}")

# #     _log(f"Response   : risk_score={final_score}, action={action}, reasons={len(reasons)} items")
# #     _log("---")

# #     return {
# #         "risk_score": final_score,
# #         "action":     action,
# #         "reasons":    reasons,
# #     }

# def assess(transaction: dict) -> dict:
#     # 1. Sanitise & Inject Features
#     tx = _sanitise(transaction)
#     user_id = tx["user_id"]
    
#     # 2. Get History (Last 4, because current_tx will make it 5)
#     history = get_history(user_id)

#     # 3. Rule Engine
#     rule_result = _rule_mod.evaluate(tx, history)
#     rule_score = rule_result.get("rule_score", 0.0)

#     # 4. LSTM with Scaling
#     try:
#         sequence = build_lstm_sequence(tx, history, max_len=SEQUENCE_LENGTH)
#         dl_result = _lstm_mod.predict(sequence)
#         dl_score = dl_result.get("dl_score", 0.5)
#     except Exception:
#         dl_score = 0.5

#     # 5. Weighted Fusion & Response
#     final_score = round((RULE_WEIGHT * rule_score) + (DL_WEIGHT * dl_score), 4)
#     action = _decide_action(final_score)
    
#     # 6. Save to History
#     append_transaction(user_id, tx)

#     return {
#         "risk_score": final_score,
#         "action": action,
#         "reasons": build_reasons(rule_result.get("flags", []), dl_score, action)
#     }


import time
from datetime import datetime
from backend.config import RULE_WEIGHT, DL_WEIGHT, SEQUENCE_LENGTH
import backend.services.rule_engine as _rule_mod
import backend.services.lstm_service as _lstm_mod
from backend.services.sequence_builder import build_sequence
from backend.db.database import get_history, append_transaction

def _sanitise(transaction: dict) -> dict:
    tx = dict(transaction)
    ts = tx.get("timestamp")
    if ts is None:
        ts = time.time()
    tx["timestamp"] = float(ts)
    
    # 2. Force an integer hour (The likely error source)
    try:
        tx["hour"] = int(datetime.fromtimestamp(tx["timestamp"]).hour)
    except:
        tx["hour"] = 12 # Fallback to noon
    tx["timestamp"] = ts
    tx["hour"] = datetime.fromtimestamp(ts).hour
    
    # Injecting the 8-feature defaults for the LSTM
    tx["amount_zscore"] = tx.get("amount_zscore", 0.0)
    tx["tx_frequency_60m"] = tx.get("tx_frequency_60m", 1.0)
    tx["device_fingerprint"] = tx.get("device_fingerprint", 1.0)
    tx["location_consistency"] = tx.get("location_consistency", 1)
    tx["category_risk"] = tx.get("category_risk", 0.1)
    tx["account_age_days"] = 365

    history = get_history(tx["user_id"])
    if history:
        amounts = [h.get("amount", 0) for h in history]
        avg = sum(amounts) / len(amounts)
        # Simple Z-Score: how far is this from the average?
        tx["amount_zscore"] = (tx["amount"] - avg) / (avg if avg > 0 else 1)
    else:
        tx["amount_zscore"] = 0.0

    # 4. Standardize all other LSTM features as floats
    tx["tx_frequency_60m"] = float(tx.get("tx_frequency_60m", 1.0))
    tx["device_fingerprint"] = float(tx.get("device_fingerprint", 1.0))
    tx["location_consistency"] = int(tx.get("location_consistency", 1))
    tx["category_risk"] = float(tx.get("category_risk", 0.1))
    tx["account_age_days"] = 365
            
    return tx

def assess(transaction: dict) -> dict:
    tx = _sanitise(transaction)
    amount = tx.get("amount", 0)
    user_id = tx.get("user_id", "unknown")
    history = get_history(user_id) # Fetches last 4 from database.py

    # Rule Engine Assessment
    rule_res = _rule_mod.evaluate(tx, history)
    rule_score = rule_res.get("rule_score", 0.0)

    # LSTM Assessment
    sequence = build_sequence(tx, history, max_len=SEQUENCE_LENGTH)
    dl_res = _lstm_mod.predict(sequence)
    dl_score = dl_res.get("dl_score", 0.5)

    # ── SENSITIVITY DAMPING ──────────────────────────────────────────────
    # If it's a small transaction (< ₹500), we artificially lower the 
    # influence of the AI to prevent "New User" anxiety.
    if amount < 500 and rule_score < 0.3:
        dl_score = dl_score * 0.5 
    # ─────────────────────────────────────────────────────────────────────

    # Weighted Fusion (e.g., 0.4*Rule + 0.6*DL)
    final_score = round((RULE_WEIGHT * rule_score) + (DL_WEIGHT * dl_score), 4)
    
    # Save to memory (database.py)
    append_transaction(user_id, tx)

    if amount > 150000:
        return {
            "risk_score": 1.0,
            "action": "BLOCK",
            "reasons": ["CRITICAL: Amount exceeds unauthorized limit."]
        }

    return {
        "risk_score": final_score,
        "action": "BLOCK" if final_score > 0.75 else "VERIFY" if final_score > 0.4 else "ALLOW",
        "reasons": rule_res.get("flags", [])
    }