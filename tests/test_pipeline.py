# tests/test_pipeline.py
"""
Fraud Interceptor - Full Pipeline Test
=======================================
HOW TO RUN:
    Open terminal in your fraud-interceptor/ folder
    
    Windows:
        set PYTHONPATH=.
        python tests/test_pipeline.py

    Mac/Linux:
        PYTHONPATH=. python tests/test_pipeline.py

WHAT THIS TESTS:
    1. Database       - store/retrieve/window history
    2. Rule Engine    - contract compliance
    3. Sequence Builder - numpy array shape and features
    4. LSTM Service   - contract + fallback handling
    5. Explanation    - flag translation
    6. Full Pipeline  - end-to-end assess() call
"""

import sys
import os

# ── Make sure Python can find the backend package ──────────────────────────
# This line adds fraud-interceptor/ to sys.path so "from backend.X import Y" works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import numpy as np

# ── Imports ─────────────────────────────────────────────────────────────────
print("Importing modules...")
try:
    from backend.db.database               import get_history, append_transaction, clear_history
    from backend.services.rule_engine      import evaluate
    from backend.services.lstm_service     import predict
    from backend.services.sequence_builder import build_sequence
    from backend.services.explanation      import build_reasons
    from backend.services.risk_engine      import assess
    print("All imports successful.\n")
except ImportError as e:
    print(f"\nIMPORT FAILED: {e}")
    print("\nFix: make sure you have __init__.py in:")
    print("  backend/__init__.py")
    print("  backend/services/__init__.py")
    print("  backend/routes/__init__.py")
    print("  backend/db/__init__.py")
    print("\nAnd run from fraud-interceptor/ folder as:")
    print("  Windows: set PYTHONPATH=. && python tests/test_pipeline.py")
    print("  Mac/Linux: PYTHONPATH=. python tests/test_pipeline.py")
    sys.exit(1)

# ── Test runner ──────────────────────────────────────────────────────────────
passed = 0
failed = 0


def check(name, condition, got=None, expected=None):
    global passed, failed
    if condition:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name}")
        if expected is not None:
            print(f"        Expected : {expected}")
        if got is not None:
            print(f"        Got      : {got}")
        failed += 1


def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# ════════════════════════════════════════════════════════
#  1. DATABASE
# ════════════════════════════════════════════════════════
section("1. DATABASE  (backend/db/database.py)")
print("""
What this tests:
  - New users have empty history
  - Transactions are stored in order
  - History is capped at 5 entries (sliding window)

Expected results:
  - get_history("new_user") -> []
  - After 2 appends -> history length = 2
  - After 8 appends -> history length = 5 (oldest 3 evicted)
""")

clear_history("db_test")
h = get_history("db_test")
check("New user has empty history", h == [], got=h, expected=[])

append_transaction("db_test", {"amount": 100, "recipient": "a@upi"})
append_transaction("db_test", {"amount": 200, "recipient": "b@upi"})
h = get_history("db_test")
check("2 transactions stored correctly", len(h) == 2, got=len(h), expected=2)
check("Order preserved (oldest first)", h[0]["amount"] == 100 and h[1]["amount"] == 200)

clear_history("window_test")
for i in range(8):
    append_transaction("window_test", {"amount": i * 100})
h = get_history("window_test")
check("Window capped at 5 entries after 8 appends", len(h) == 5, got=len(h), expected=5)
check("Oldest entries evicted (first entry should be 300)", h[0]["amount"] == 300,
      got=h[0]["amount"], expected=300)


# ════════════════════════════════════════════════════════
#  2. RULE ENGINE
# ════════════════════════════════════════════════════════
section("2. RULE ENGINE  (backend/services/rule_engine.py)")
print("""
What this tests:
  - Function returns required keys: rule_score, flags
  - Score is in valid range [0.0, 1.0]
  - Handles empty history (first-time user)
  - Handles empty transaction dict without crashing

Expected results:
  - Returns dict with "rule_score" (float) and "flags" (list)
  - Score between 0.0 and 1.0
  - Currently returns 0.5 (dummy placeholder)
""")

tx = {"user_id": "u1", "amount": 5000, "recipient": "test@upi"}
history = [{"amount": 1000}, {"amount": 1200}]
result = evaluate(tx, history)

check("Returns dict",                  isinstance(result, dict), got=type(result))
check("Has 'rule_score' key",          "rule_score" in result, got=list(result.keys()))
check("Has 'flags' key",               "flags" in result, got=list(result.keys()))
check("rule_score is float",           isinstance(result["rule_score"], float))
check("flags is list",                 isinstance(result["flags"], list))
check("rule_score in [0.0, 1.0]",      0.0 <= result["rule_score"] <= 1.0,
      got=result["rule_score"])
check("Works with empty history",      evaluate(tx, []) is not None)
check("Works with empty transaction",  evaluate({}, []) is not None)

print(f"\n  Current output: {result}")
print("  (Dummy: 0.5 expected until teammate implements real rules)")


# ════════════════════════════════════════════════════════
#  3. SEQUENCE BUILDER
# ════════════════════════════════════════════════════════
section("3. SEQUENCE BUILDER  (backend/services/sequence_builder.py)")
print("""
What this tests:
  - Output shape is exactly (1, 5, 4)
  - Zero-padding works when history is short
  - Features are computed correctly:
      [amount, hour, deviation, velocity]
  - dtype is float32 (required for Keras/PyTorch)

Expected results:
  - Array shape: (1, 5, 4) always
  - With no history: first 4 rows are [0,0,0,0], last row has real data
  - deviation = 1.0 when all amounts are the same
  - hour = 12.0 when no timestamp given
""")

tx_seq = {"amount": 5000.0}
arr_no_history = build_sequence(tx_seq, [], max_len=5)

check("Shape is (1, 5, 4) with no history",
      arr_no_history.shape == (1, 5, 4), got=arr_no_history.shape, expected=(1,5,4))
check("dtype is float32",
      arr_no_history.dtype == np.float32, got=arr_no_history.dtype)
check("Amount in last row [0]",
      arr_no_history[0, -1, 0] == 5000.0, got=arr_no_history[0, -1, 0])
check("Hour defaults to 12 when no timestamp",
      arr_no_history[0, -1, 1] == 12.0, got=arr_no_history[0, -1, 1])
check("First 4 rows are zero-padded",
      all(arr_no_history[0, i, 0] == 0.0 for i in range(4)))

# Deviation test: all same amount → deviation should be 1.0
history_uniform = [{"amount": 500}] * 4
tx_uniform = {"amount": 500}
arr_uniform = build_sequence(tx_uniform, history_uniform, max_len=5)
deviations = arr_uniform[0, :, 2]
check("Deviation = 1.0 when all amounts equal",
      all(abs(d - 1.0) < 1e-5 for d in deviations), got=deviations.tolist())

# Full history test
history_full = [{"amount": i * 100} for i in range(1, 5)]
arr_full = build_sequence({"amount": 500}, history_full, max_len=5)
check("Shape is (1, 5, 4) with full history",
      arr_full.shape == (1, 5, 4), got=arr_full.shape)

print(f"\n  Sample sequence (no history):\n{arr_no_history}")


# ════════════════════════════════════════════════════════
#  4. LSTM SERVICE
# ════════════════════════════════════════════════════════
section("4. LSTM SERVICE  (backend/services/lstm_service.py)")
print("""
What this tests:
  - Returns required key: dl_score
  - Score is in valid range [0.0, 1.0]
  - Fallback works for None, [], empty numpy array

Expected results:
  - Returns dict with "dl_score" (float)
  - Currently returns 0.5 (dummy placeholder)
  - None input → 0.5
  - Empty list → 0.5
  - Empty numpy array → 0.5
""")

arr = build_sequence({"amount": 1000}, [], max_len=5)
result_lstm = predict(arr)

check("Returns dict",            isinstance(result_lstm, dict), got=type(result_lstm))
check("Has 'dl_score' key",      "dl_score" in result_lstm, got=list(result_lstm.keys()))
check("dl_score is float",       isinstance(result_lstm["dl_score"], float))
check("dl_score in [0.0, 1.0]",  0.0 <= result_lstm["dl_score"] <= 1.0,
      got=result_lstm["dl_score"])
check("Fallback: None → 0.5",    predict(None)["dl_score"] == 0.5)
check("Fallback: [] → 0.5",      predict([])["dl_score"] == 0.5)
check("Fallback: np.array([]) → 0.5", predict(np.array([]))["dl_score"] == 0.5)

print(f"\n  Current output: {result_lstm}")
print("  (Dummy: 0.5 expected until teammate implements real LSTM model)")


# ════════════════════════════════════════════════════════
#  5. EXPLANATION ENGINE
# ════════════════════════════════════════════════════════
section("5. EXPLANATION ENGINE  (backend/services/explanation.py)")
print("""
What this tests:
  - Known flags are translated to readable strings
  - BLOCK action adds a block message
  - VERIFY action adds a verify message
  - High DL score adds AI anomaly message
  - ALLOW with no flags returns empty list (no noise)

Expected results:
  - NEW_RECIPIENT flag → "...recipient you have never transacted with..."
  - dl_score 0.85 → "AI model detected a strong anomaly..."
  - action BLOCK → "Transaction has been BLOCKED..."
  - ALLOW + no flags + low dl_score → []
""")

r_block = build_reasons(["NEW_RECIPIENT", "ODD_HOUR"], 0.85, "BLOCK")
check("NEW_RECIPIENT flag translated",
      any("recipient" in s.lower() for s in r_block), got=r_block)
check("ODD_HOUR flag translated",
      any("hour" in s.lower() or "unusual" in s.lower() for s in r_block), got=r_block)
check("High DL score adds AI message",
      any("AI" in s for s in r_block), got=r_block)
check("BLOCK adds block message",
      any("BLOCKED" in s for s in r_block), got=r_block)

r_verify = build_reasons(["AMOUNT_DEVIATION"], 0.6, "VERIFY")
check("AMOUNT_DEVIATION flag translated",
      any("amount" in s.lower() or "spending" in s.lower() for s in r_verify), got=r_verify)
check("VERIFY adds verify message",
      any("verify" in s.lower() for s in r_verify), got=r_verify)

r_allow = build_reasons([], 0.3, "ALLOW")
check("ALLOW + no flags + low DL = empty reasons", r_allow == [], got=r_allow)

print(f"\n  BLOCK reasons: {r_block}")
print(f"  ALLOW reasons: {r_allow}")


# ════════════════════════════════════════════════════════
#  6. FULL PIPELINE  (end-to-end)
# ════════════════════════════════════════════════════════
section("6. FULL PIPELINE  (backend/services/risk_engine.py)")
print("""
What this tests:
  - assess() returns all 3 required API keys
  - risk_score is float in [0.0, 1.0]
  - action is one of ALLOW / VERIFY / BLOCK
  - reasons is a list
  - With dummy modules: 0.4*0.5 + 0.6*0.5 = 0.5 exactly
  - 0.5 → VERIFY (≥ 0.50 threshold)
  - History grows after each call
  - Response time < 200ms

Expected results for a fresh user sending 1 transaction:
  risk_score : 0.5
  action     : VERIFY
  reasons    : ["Please verify this transaction before proceeding."]
""")

# Fresh user
clear_history("pipeline_u1")
tx_test = {"user_id": "pipeline_u1", "amount": 5000, "recipient": "test@upi"}

t0 = time.time()
result_pipeline = assess(tx_test)
elapsed_ms = (time.time() - t0) * 1000

check("Returns dict",                  isinstance(result_pipeline, dict))
check("Has 'risk_score'",              "risk_score" in result_pipeline)
check("Has 'action'",                  "action" in result_pipeline)
check("Has 'reasons'",                 "reasons" in result_pipeline)
check("risk_score is float",           isinstance(result_pipeline["risk_score"], float))
check("risk_score in [0.0, 1.0]",      0.0 <= result_pipeline["risk_score"] <= 1.0)
check("action is valid string",        result_pipeline["action"] in ("ALLOW", "VERIFY", "BLOCK"),
      got=result_pipeline["action"])
check("reasons is list",               isinstance(result_pipeline["reasons"], list))
check("Dummy score = 0.5 exactly",
      result_pipeline["risk_score"] == 0.5, got=result_pipeline["risk_score"], expected=0.5)
check("Action = VERIFY for score 0.5",
      result_pipeline["action"] == "VERIFY", got=result_pipeline["action"], expected="VERIFY")
check("Response under 200ms",          elapsed_ms < 200,
      got=f"{elapsed_ms:.1f}ms", expected="<200ms")

# History grows
h_after = get_history("pipeline_u1")
check("Transaction saved to history",  len(h_after) == 1, got=len(h_after), expected=1)

# Second transaction - history now has 1 entry
result2 = assess({"user_id": "pipeline_u1", "amount": 3000, "recipient": "shop@upi"})
check("Second call also returns valid response",
      result2["action"] in ("ALLOW", "VERIFY", "BLOCK"))
check("History grows to 2 after 2 calls",
      len(get_history("pipeline_u1")) == 2)

print(f"\n  Full pipeline output:")
print(f"    risk_score : {result_pipeline['risk_score']}")
print(f"    action     : {result_pipeline['action']}")
print(f"    reasons    : {result_pipeline['reasons']}")
print(f"    time       : {elapsed_ms:.2f}ms")


# ════════════════════════════════════════════════════════
#  SUMMARY
# ════════════════════════════════════════════════════════
total = passed + failed
print(f"\n{'='*55}")
print(f"  RESULTS: {passed}/{total} passed", end="")
if failed == 0:
    print("  ---  All good! System ready for teammate integration.")
else:
    print(f"  ---  {failed} FAILED. Fix errors above before integrating.")
print(f"{'='*55}\n")

if failed > 0:
    sys.exit(1)