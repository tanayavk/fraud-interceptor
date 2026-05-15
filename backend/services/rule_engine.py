# backend/services/rule_engine.py
"""
Rule Engine — Cybersecurity Layer
==================================
CONTRACT: evaluate(transaction, history) -> {"rule_score": float, "flags": list[str]}

Each rule contributes an additive weight to rule_score (capped at 1.0).
Rules are ordered from highest signal strength to lowest.

Demo thresholds are tuned for the ₹500 – ₹149,999 mid-tier range that
reaches this engine (amounts outside that range are short-circuited in
risk_engine.py before we're called).
"""

from datetime import datetime


# ─── Rule weights (must sum ≤ 1.0 to keep score in [0, 1]) ──────────────────
W_AMOUNT_SPIKE      = 0.40   # amount >> user's personal average
W_NEW_RECIPIENT     = 0.20   # first time sending to this UPI address
W_ODD_HOUR          = 0.15   # transaction between 00:00 – 05:59
W_RAPID_REPEAT      = 0.15   # > 2 transactions already in history (velocity proxy)
W_ROUND_LARGE       = 0.10   # large round-number amount (mule-account pattern)


def evaluate(transaction: dict, history: list) -> dict:
    """
    Args:
        transaction : sanitised dict from risk_engine._sanitise()
        history     : list of past transaction dicts (may be empty)

    Returns:
        {"rule_score": float [0.0 – 1.0], "flags": list[str]}
    """
    if not transaction:
        return {"rule_score": 0.0, "flags": ["MISSING_TRANSACTION_DATA"]}

    rule_score = 0.0
    flags: list[str] = []

    amount    = float(transaction.get("amount") or 0.0)
    recipient = str(transaction.get("recipient") or "").strip().lower()
    hour      = int(transaction.get("hour") or 0)

    # ── Rule 1: Amount spike vs personal baseline ─────────────────────────────
    # Triggers when the current amount is > 3× the user's own average.
    # This catches sudden large spikes even for amounts well below 150k.
    if history:
        amounts = [float(h.get("amount") or 0.0) for h in history if isinstance(h, dict)]
        if amounts:
            avg = sum(amounts) / len(amounts)
            if avg > 0 and amount >= 3.0 * avg:
                rule_score += W_AMOUNT_SPIKE
                flags.append(f"AMOUNT_SPIKE: ₹{amount:,.0f} is {amount/avg:.1f}× your average")

    # ── Rule 2: New / unseen recipient ────────────────────────────────────────
    # First time this user is sending to this UPI ID.
    if recipient and history:
        known = {str(h.get("recipient") or "").strip().lower() for h in history if isinstance(h, dict)}
        if recipient not in known:
            rule_score += W_NEW_RECIPIENT
            flags.append(f"NEW_RECIPIENT: {recipient} not seen before")

    # ── Rule 3: Odd-hour transaction ──────────────────────────────────────────
    # Transactions between midnight and 6 AM are statistically anomalous.
    if 0 <= hour < 6:
        rule_score += W_ODD_HOUR
        flags.append(f"ODD_HOUR: sent at {hour:02d}:xx (late-night activity)")

    # ── Rule 4: High transaction velocity ────────────────────────────────────
    # More than 2 prior transactions in the stored window suggests rapid-fire
    # behaviour (the window holds at most 5, so > 2 = moderate velocity).
    if len(history) > 2:
        rule_score += W_RAPID_REPEAT
        flags.append(f"HIGH_VELOCITY: {len(history)} recent transactions on record")

    # ── Rule 5: Large round-number transfer ───────────────────────────────────
    # Amounts like 50,000 / 75,000 / 100,000 are common in mule-account scams.
    # Only flags amounts ≥ 10,000 that are exact multiples of 5,000.
    if amount >= 10_000 and amount % 5_000 == 0:
        rule_score += W_ROUND_LARGE
        flags.append(f"ROUND_LARGE_AMOUNT: ₹{amount:,.0f} is a suspicious round figure")

    rule_score = round(min(rule_score, 1.0), 4)
    return {"rule_score": rule_score, "flags": flags}