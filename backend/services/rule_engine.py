# backend/services/rule_engine.py
"""
Rule Engine - Cybersecurity Layer
CONTRACT: evaluate(transaction, history) -> {"rule_score": float, "flags": list[str]}
STATUS: Dummy placeholder - returns 0.5 safe default.
TEAMMATE (Cybersecurity): Replace the body of evaluate() with real checks.
DO NOT rename the function. DO NOT change return keys.
"""


def evaluate(transaction: dict, history: list) -> dict:
    """
    Args:
        transaction : dict  e.g. {"user_id": "u1", "amount": 5000, "recipient": "x@upi"}
        history     : list  list of past transaction dicts, may be empty

    Returns:
        {"rule_score": float [0.0-1.0], "flags": list[str]}
    """
    # Guard: malformed input
    if not transaction:
        return {"rule_score": 0.5, "flags": ["MISSING_TRANSACTION_DATA"]}

    # ----------------------------------------------------------------
    # DUMMY RULES — replace these with real checks
    # ----------------------------------------------------------------
    rule_score = 0.5
    flags = []

    # Example skeleton your teammate will fill in:
    # amount = transaction.get("amount", 0)
    # if history:
    #     avg = sum(t.get("amount",0) for t in history) / len(history)
    #     if amount > 3 * avg:
    #         rule_score += 0.3
    #         flags.append("AMOUNT_DEVIATION")
    # recipient = transaction.get("recipient", "")
    # known = [t.get("recipient","") for t in history]
    # if recipient not in known:
    #     rule_score += 0.2
    #     flags.append("NEW_RECIPIENT")
    # rule_score = min(rule_score, 1.0)

    return {
        "rule_score": rule_score,
        "flags": flags
    }