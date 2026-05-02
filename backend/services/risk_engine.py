"""
Risk Engine — Core Brain
==========================
Orchestrates the full fraud assessment pipeline:

  route  →  risk_engine
                ├─ rule_engine.evaluate(transaction, history)
                ├─ lstm_service.predict(sequence)
                ├─ score combination
                ├─ action decision
                └─ explanation.build_reasons(...)

This is the ONLY file the route needs to import.
Neither the route nor this file should be modified when teammates
swap in their real rule / DL implementations.
"""

from backend.services.rule_engine      import evaluate       as rule_evaluate
from backend.services.lstm_service    import predict         as dl_predict
from backend.services.explanation     import build_reasons
from backend.services.sequence_builder import build_sequence  as build_lstm_sequence
from backend.db.database              import get_history, append_transaction

# ---------------------------------------------------------------------------
# Score weighting (adjust here only — nowhere else)
# ---------------------------------------------------------------------------
_RULE_WEIGHT = 0.4
_DL_WEIGHT   = 0.6

# ---------------------------------------------------------------------------
# Action thresholds
# ---------------------------------------------------------------------------
_BLOCK_THRESHOLD  = 0.75
_VERIFY_THRESHOLD = 0.50


def _decide_action(final_score: float) -> str:
    """Maps a combined risk score to a decisioning action."""
    if final_score >= _BLOCK_THRESHOLD:
        return "BLOCK"
    if final_score >= _VERIFY_THRESHOLD:
        return "VERIFY"
    return "ALLOW"


def assess(transaction: dict) -> dict:
    """
    Full fraud risk assessment for a single transaction.

    Args:
        transaction : dict — must contain at minimum:
                             { "user_id": str, "amount": float, "recipient": str }

    Returns:
        dict — strict API response format:
               {
                   "risk_score" : float,        # combined score [0.0 – 1.0]
                   "action"     : str,           # "ALLOW" | "VERIFY" | "BLOCK"
                   "reasons"    : list[str]      # human-readable explanations
               }
    """
    user_id = transaction.get("user_id", "unknown")

    # ------------------------------------------------------------------
    # 1. Fetch user history from DB
    # ------------------------------------------------------------------
    history: list[dict] = get_history(user_id)

    # ------------------------------------------------------------------
    # 2. Rule Engine
    # ------------------------------------------------------------------
    rule_result: dict = rule_evaluate(transaction, history)
    rule_score: float = float(rule_result.get("rule_score", 0.5))
    flags: list[str]  = rule_result.get("flags", [])

    # ------------------------------------------------------------------
    # 3. Deep Learning (LSTM)
    # ------------------------------------------------------------------
    # sequence shape: (1, max_len=5, 4 features)
    # features per timestep: [amount, hour, deviation, velocity]
    sequence        = build_lstm_sequence(transaction, history)
    dl_result: dict = dl_predict(sequence)
    dl_score: float = float(dl_result.get("dl_score", 0.5))

    # ------------------------------------------------------------------
    # 4. Combine scores
    # ------------------------------------------------------------------
    final_score: float = round(
        _RULE_WEIGHT * rule_score + _DL_WEIGHT * dl_score,
        4
    )

    # ------------------------------------------------------------------
    # 5. Decide action
    # ------------------------------------------------------------------
    action: str = _decide_action(final_score)

    # ------------------------------------------------------------------
    # 6. Build human-readable explanation
    # ------------------------------------------------------------------
    reasons: list[str] = build_reasons(flags, dl_score, action)

    # ------------------------------------------------------------------
    # 7. Persist transaction to history (after assessment, not before)
    # ------------------------------------------------------------------
    append_transaction(user_id, transaction)

    # ------------------------------------------------------------------
    # 8. Return strict API response
    # ------------------------------------------------------------------
    return {
        "risk_score": final_score,
        "action":     action,
        "reasons":    reasons,
    }