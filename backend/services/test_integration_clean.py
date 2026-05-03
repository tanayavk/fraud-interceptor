"""
Fraud Interceptor - Rule Engine Integration Test
===============================================
Demonstrates how Rule Engine integrates with DL model in the backend orchestrator.

This simulates the backend coordination WITHOUT actually implementing the DL model.
The integration is contract-based and modular.
"""

import json
from rule_engine import evaluate as rule_evaluate


def simulate_backend_orchestrator(transaction, history, use_dl=False):
    """
    Simulates the backend orchestrator that coordinates Rule Engine + DL Model.
    """
    print("\n" + "=" * 70)
    print("BACKEND ORCHESTRATOR SIMULATION")
    print("=" * 70)

    # STEP 1: Call Rule Engine (ALWAYS SUCCEEDS)
    print("\n[1] Calling Rule Engine...")
    rule_result = rule_evaluate(transaction, history)
    rule_score = rule_result["rule_score"]
    rule_flags = rule_result["flags"]

    print(f"    ✓ Rule Score: {rule_score}")
    print(f"    ✓ Flags: {rule_flags}")

    # STEP 2: Call DL Model (WITH FALLBACK)
    print("\n[2] Calling DL Model (simulated)...")
    if use_dl:
        try:
            dl_score = 0.6
            print(f"    ✓ DL Score: {dl_score}")
        except Exception as e:
            print(f"    ✗ DL Model failed: {str(e)}")
            print(f"    ⚠ Falling back to DL Score = 0.5")
            dl_score = 0.5
    else:
        print("    ⊘ DL Model disabled (simulating unavailability)")
        dl_score = 0.5

    # STEP 3: Combine Scores
    print("\n[3] Combining Scores...")
    alpha_rule = 0.4
    alpha_dl = 0.6
    final_score = (alpha_rule * rule_score) + (alpha_dl * dl_score)

    print(f"    Rule Score:   {rule_score:.4f} × {alpha_rule} = {rule_score * alpha_rule:.4f}")
    print(f"    DL Score:     {dl_score:.4f} × {alpha_dl} = {dl_score * alpha_dl:.4f}")
    print(f"    Final Score:  {final_score:.4f}")

    # STEP 4: Determine Action
    print("\n[4] Determining Action...")
    if final_score >= 0.7:
        action = "BLOCK"
        print(f"    🔴 {action} (score >= 0.7)")
    elif final_score >= 0.5:
        action = "VERIFY"
        print(f"    🟡 {action} (0.5 <= score < 0.7)")
    else:
        action = "ALLOW"
        print(f"    🟢 {action} (score < 0.5)")

    # STEP 5: Generate Explanation
    print("\n[5] Generating Explanation...")
    reasons = rule_flags if rule_flags else ["Transaction appears normal"]
    print(f"    Reasons: {reasons}")

    # STEP 6: Response
    print("\n[6] Final Response to Client...")
    response = {
        "risk_score": round(final_score, 4),
        "action": action,
        "reasons": reasons
    }
    print(json.dumps(response, indent=2))

    return response


def test_scenario_1_normal_transaction():
    """Normal transaction - should ALLOW"""
    print("\n\n" + "█" * 70)
    print("SCENARIO 1: Normal Transaction")
    print("█" * 70)

    transaction = {
        "amount": 100.0,
        "recipient": "alice@upi",
        "timestamp": 1672531200,
        "device_id": "device_1"
    }

    history = [
        {"amount": 95.0, "recipient": "alice@upi", "timestamp": 1672444800, "device_id": "device_1"},
        {"amount": 110.0, "recipient": "alice@upi", "timestamp": 1672358400, "device_id": "device_1"},
    ]

    result = simulate_backend_orchestrator(transaction, history, use_dl=True)
    assert result["action"] == "ALLOW", f"Expected ALLOW, got {result['action']}"
    print("\n✅ TEST PASSED: Normal transaction allowed")


def test_scenario_2_high_amount_deviation():
    """High amount deviation - rule engine detects and flags it"""
    print("\n\n" + "█" * 70)
    print("SCENARIO 2: High Amount Deviation")
    print("█" * 70)

    transaction = {
        "amount": 5000.0,
        "recipient": "alice@upi",
        "timestamp": 1672531200,
        "device_id": "device_1"
    }

    history = [
        {"amount": 100.0, "recipient": "alice@upi", "timestamp": 1672444800, "device_id": "device_1"},
        {"amount": 95.0, "recipient": "alice@upi", "timestamp": 1672358400, "device_id": "device_1"},
    ]

    result = simulate_backend_orchestrator(transaction, history, use_dl=True)
    assert "high_amount_deviation" in result["reasons"], f"Expected flag, got {result['reasons']}"
    assert result["risk_score"] > 0.36, f"Expected score > 0.36, got {result['risk_score']}"
    print("\n✅ TEST PASSED: High amount deviation detected and flagged")


def test_scenario_3_new_recipient_with_multiple_rules():
    """New recipient + new device + odd hour - multiple rules trigger"""
    print("\n\n" + "█" * 70)
    print("SCENARIO 3: Multiple Rules Triggered")
    print("█" * 70)

    odd_hour_ts = 1672499000

    transaction = {
        "amount": 500.0,
        "recipient": "charlie@upi",
        "timestamp": odd_hour_ts,
        "device_id": "device_new"
    }

    history = [
        {"amount": 100.0, "recipient": "alice@upi", "timestamp": 1672444800, "device_id": "device_1"},
    ]

    result = simulate_backend_orchestrator(transaction, history, use_dl=True)
    assert len(result["reasons"]) >= 2, f"Expected >=2 flags, got {result['reasons']}"
    assert result["risk_score"] >= 0.4, f"Expected score >= 0.4, got {result['risk_score']}"
    print(f"\n✅ TEST PASSED: Multiple rules detected")
    print(f"   Flags triggered: {result['reasons']}")


def test_scenario_4_dl_model_unavailable():
    """DL Model unavailable - Rule Engine still works (fallback)"""
    print("\n\n" + "█" * 70)
    print("SCENARIO 4: DL Model Unavailable (Fallback)")
    print("█" * 70)

    transaction = {
        "amount": 2000.0,
        "recipient": "bob@upi",
        "timestamp": 1672531200,
        "device_id": "device_1"
    }

    history = [
        {"amount": 100.0, "recipient": "alice@upi", "timestamp": 1672444800, "device_id": "device_1"},
    ]

    result = simulate_backend_orchestrator(transaction, history, use_dl=False)
    assert result["action"] in ["ALLOW", "VERIFY", "BLOCK"], f"Invalid action: {result['action']}"
    assert "high_amount_deviation" in result["reasons"], f"Expected flag, got {result['reasons']}"
    print(f"\n✅ TEST PASSED: System works even without DL model")
    print(f"   Final action: {result['action']}")


def test_scenario_5_empty_history():
    """First transaction from user - no history"""
    print("\n\n" + "█" * 70)
    print("SCENARIO 5: First Transaction (Empty History)")
    print("█" * 70)

    transaction = {
        "amount": 500.0,
        "recipient": "alice@upi",
        "timestamp": 1672531200,
        "device_id": "device_1"
    }

    history = []

    result = simulate_backend_orchestrator(transaction, history, use_dl=True)
    assert result["action"] in ["ALLOW", "VERIFY"], f"Expected ALLOW/VERIFY, got {result['action']}"
    assert 0 <= result["risk_score"] <= 1, f"Invalid score: {result['risk_score']}"
    print(f"\n✅ TEST PASSED: First transaction handled gracefully")
    print(f"   Final action: {result['action']}")


def test_scenario_6_high_velocity_attack():
    """Rapid-fire transactions - suspicious velocity"""
    print("\n\n" + "█" * 70)
    print("SCENARIO 6: High Velocity Attack (Bot Activity)")
    print("█" * 70)

    current_ts = 1672531200

    transaction = {
        "amount": 100.0,
        "recipient": "alice@upi",
        "timestamp": current_ts,
        "device_id": "device_1"
    }

    history = [
        {"amount": 50.0, "recipient": "alice@upi", "timestamp": current_ts - 60, "device_id": "device_1"},
        {"amount": 50.0, "recipient": "alice@upi", "timestamp": current_ts - 120, "device_id": "device_1"},
        {"amount": 50.0, "recipient": "alice@upi", "timestamp": current_ts - 180, "device_id": "device_1"},
    ]

    result = simulate_backend_orchestrator(transaction, history, use_dl=True)
    assert "high_transaction_velocity" in result["reasons"], f"Expected velocity flag, got {result['reasons']}"
    assert result["risk_score"] >= 0.3, f"Expected score >= 0.3, got {result['risk_score']}"
    print("\n✅ TEST PASSED: High velocity attack detected")


def run_all_tests():
    """Run all integration tests"""
    print("\n\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "FRAUD INTERCEPTOR - INTEGRATION TESTS" + " " * 17 + "║")
    print("║" + " " * 15 + "Rule Engine + Backend Orchestration" + " " * 19 + "║")
    print("╚" + "═" * 68 + "╝")

    try:
        test_scenario_1_normal_transaction()
        test_scenario_2_high_amount_deviation()
        test_scenario_3_new_recipient_with_multiple_rules()
        test_scenario_4_dl_model_unavailable()
        test_scenario_5_empty_history()
        test_scenario_6_high_velocity_attack()

        print("\n\n")
        print("╔" + "═" * 68 + "╗")
        print("║" + " " * 20 + "✅ ALL TESTS PASSED ✅" + " " * 24 + "║")
        print("║" + " " * 16 + "Rule Engine integrates seamlessly with backend" + " " * 8 + "║")
        print("╚" + "═" * 68 + "╝\n")

    except AssertionError as e:
        print(f"\n\n❌ TEST FAILED: {str(e)}\n")
        raise


if __name__ == "__main__":
    run_all_tests()