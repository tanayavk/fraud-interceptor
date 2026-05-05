from .rule_engine import check_cyber_rules
from .lstm_service import predict as get_dl_score

def calculate_final_risk(transaction_data, user_history_sequence):
    """
    Orchestrates the Hybrid Risk Assessment.
    
    Args:
        transaction_data (dict): Current transaction details (amt, hr, dist, etc.)
        user_history_sequence (list): Last N transaction features for LSTM
        
    Returns:
        dict: Final risk analysis including scores and decision
    """
    
    # 1. TIER 1: CYBER HEURISTICS (Rule Engine)
    # Returns a score from 0 to 1 based on velocity, blacklists, and limits
    rule_results = check_cyber_rules(transaction_data)
    rule_score = rule_results.get("rule_score", 0.0)
    triggered_rules = rule_results.get("triggered_rules", [])

    # 2. TIER 2: DEEP LEARNING (LSTM Core)
    # Processes the sequence of transactions to find behavioral patterns
    dl_results = get_dl_score(user_history_sequence)
    dl_score = dl_results.get("dl_score", 0.5)

    # 3. HYBRID INTEGRATION (Weightage)
    # Industry Standard: 40% Rules (Deterministic) + 60% DL (Probabilistic)
    final_risk_score = (0.4 * rule_score) + (0.6 * dl_score)

    # 4. ADAPTIVE ACTION DECISION
    decision = "APPROVE"
    if final_risk_score > 0.75:
        decision = "BLOCK"
    elif final_risk_score > 0.40:
        decision = "CHALLENGE_MFA"  # Trigger OTP/Biometric

    return {
        "final_risk_score": round(final_risk_score, 4),
        "decision": decision,
        "breakdown": {
            "rule_contribution": round(rule_score, 2),
            "dl_contribution": round(dl_score, 2),
            "triggered_rules": triggered_rules
        }
    }