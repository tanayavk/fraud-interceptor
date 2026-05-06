# backend/services/explanation.py
"""
Explanation Engine
Converts rule flags + DL score into human-readable reason strings.
"""

_FLAG_MESSAGES = {
    "AMOUNT_DEVIATION":         "Transaction amount is significantly higher than your usual spending.",
    "NEW_RECIPIENT":            "Money is being sent to a recipient you have never transacted with before.",
    "HIGH_VELOCITY":            "Multiple transactions detected in a very short time window.",
    "ODD_HOUR":                 "Transaction is being initiated at an unusual hour.",
    "DEVICE_ANOMALY":           "This transaction appears to originate from an unfamiliar device.",
    "MISSING_TRANSACTION_DATA": "Transaction data was incomplete or malformed.",
}


def build_reasons(flags: list, dl_score: float, action: str) -> list:
    """
    Args:
        flags    : list[str] - rule violation codes from rule_engine
        dl_score : float     - anomaly score from lstm_service [0.0-1.0]
        action   : str       - "ALLOW" | "VERIFY" | "BLOCK"

    Returns:
        list[str] - plain-English reasons for the API response
    """
    reasons = []

    # Translate each flag
    for flag in flags:
        msg = _FLAG_MESSAGES.get(flag, f"Security check triggered: {flag}.")
        reasons.append(msg)

    # DL insight based on score
    if dl_score >= 0.75:
        reasons.append("AI model detected a strong anomaly in your recent transaction pattern.")
    elif dl_score >= 0.55:
        reasons.append("AI model flagged a mild irregularity compared to your normal activity.")

    # Action summary
    # If it's an ALLOWed transaction, we usually want it silent/empty
    if action == "ALLOW":
        return []
    elif action == "BLOCK":
        reasons.append("Transaction has been BLOCKED for your protection.")
    elif action == "VERIFY":
        reasons.append("Please verify this transaction before proceeding.")
    return reasons 
 