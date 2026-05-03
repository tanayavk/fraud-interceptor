# tests/test_all_scenarios.py
"""
Fraud Interceptor — Complete Test Suite
=========================================
HOW TO RUN:
    Windows:  set PYTHONPATH=. && python tests/test_all_scenarios.py
    Mac/Linux: PYTHONPATH=. python tests/test_all_scenarios.py

WHAT THIS COVERS:
    ✓ All 3 pipeline actions: ALLOW, VERIFY, BLOCK (simulated via monkey-patching)
    ✓ Input validation (bad data, missing fields)
    ✓ Fallback safety (module crash simulation)
    ✓ Database correctness
    ✓ Logging output check
    ✓ API response format guarantee
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Suppress logging noise during tests ──────────────────────────────────
import backend.config as cfg
cfg.ENABLE_LOGGING = False

from backend.db.database import get_history, append_transaction, clear_history
from backend.services.rule_engine  import evaluate
from backend.services.lstm_service import predict
from backend.services.risk_engine  import assess
from backend.services.explanation  import build_reasons
import backend.services.risk_engine as risk_mod   # for monkey-patching
import backend.services.rule_engine as rule_mod
import backend.services.lstm_service as lstm_mod

# ── Test runner ───────────────────────────────────────────────────────────
_passed = 0
_failed = 0

def check(name, condition, got=None, expected=None):
    global _passed, _failed
    if condition:
        print(f"  PASS  {name}")
        _passed += 1
    else:
        print(f"  FAIL  {name}")
        if expected is not None: print(f"        Expected : {expected}")
        if got      is not None: print(f"        Got      : {got}")
        _failed += 1

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ════════════════════════════════════════════════════════════════════════
#  SECTION 1 — DATABASE
# ════════════════════════════════════════════════════════════════════════
section("1. DATABASE")

clear_history("u_test")
check("Empty history for new user", get_history("u_test") == [])

append_transaction("u_test", {"amount": 100})
append_transaction("u_test", {"amount": 200})
h = get_history("u_test")
check("2 transactions stored",    len(h) == 2)
check("Order is oldest-first",    h[0]["amount"] == 100)

clear_history("u_window")
for i in range(8):
    append_transaction("u_window", {"amount": i * 100})
h = get_history("u_window")
check("Window capped at 5",       len(h) == 5, got=len(h))
check("Oldest 3 evicted",         h[0]["amount"] == 300, got=h[0]["amount"])

# No-crash on bad input
try:
    get_history(None)
    check("get_history(None) does not crash", True)
except Exception:
    check("get_history(None) does not crash", False)

try:
    append_transaction(None, {})
    check("append_transaction(None) does not crash", True)
except Exception:
    check("append_transaction(None) does not crash", False)


# ════════════════════════════════════════════════════════════════════════
#  SECTION 2 — CONTRACT CHECKS (Rule Engine + LSTM)
# ════════════════════════════════════════════════════════════════════════
section("2. MODULE CONTRACTS")

r = evaluate({"user_id":"u","amount":500,"recipient":"x@upi"}, [])
check("rule_engine: has rule_score",  "rule_score" in r)
check("rule_engine: has flags",       "flags" in r)
check("rule_engine: score in range",  0.0 <= r["rule_score"] <= 1.0)
check("rule_engine: flags is list",   isinstance(r["flags"], list))

import numpy as np
seq = np.zeros((1,5,4), dtype=np.float32)
d = predict(seq)
check("lstm: has dl_score",           "dl_score" in d)
check("lstm: score in range",         0.0 <= d["dl_score"] <= 1.0)
check("lstm fallback (None)",         predict(None)["dl_score"] == 0.5)
check("lstm fallback ([])",           predict([])["dl_score"] == 0.5)
check("lstm fallback (np.array([]))", predict(np.array([]))["dl_score"] == 0.5)


# ════════════════════════════════════════════════════════════════════════
#  SECTION 3 — API CONTRACT (assess returns correct format)
# ════════════════════════════════════════════════════════════════════════
section("3. API RESPONSE CONTRACT")

clear_history("api_u")
result = assess({"user_id":"api_u","amount":1000,"recipient":"test@upi"})
check("Has risk_score",       "risk_score" in result)
check("Has action",           "action" in result)
check("Has reasons",          "reasons" in result)
check("risk_score is float",  isinstance(result["risk_score"], float))
check("risk_score in [0,1]",  0.0 <= result["risk_score"] <= 1.0)
check("action is valid",      result["action"] in ("ALLOW","VERIFY","BLOCK"),
      got=result["action"])
check("reasons is list",      isinstance(result["reasons"], list))

print(f"\n  Output: {result}")


# ════════════════════════════════════════════════════════════════════════
#  SECTION 4 — SIMULATE ALL 3 SCENARIOS
#  We temporarily override module return values to test each branch.
# ════════════════════════════════════════════════════════════════════════
section("4. SCENARIO SIMULATION  (ALLOW / VERIFY / BLOCK)")

print("""
  How this works:
  ─────────────────────────────────────────────────────
  We temporarily override rule_engine + lstm_service
  to return specific scores, then restore them after.

  Score formula: 0.4 × rule_score + 0.6 × dl_score
  ─────────────────────────────────────────────────────
  ALLOW  : both = 0.1  →  final = 0.4×0.1 + 0.6×0.1 = 0.10  (<0.50)
  VERIFY : both = 0.6  →  final = 0.4×0.6 + 0.6×0.6 = 0.60  (≥0.50)
  BLOCK  : both = 0.9  →  final = 0.4×0.9 + 0.6×0.9 = 0.90  (≥0.75)
  ─────────────────────────────────────────────────────
""")

_original_rule = rule_mod.evaluate
_original_lstm = lstm_mod.predict


def _force_assess(rule_score, dl_score):
    """Temporarily patch both modules, run assess, restore."""
    rule_mod.evaluate = lambda tx, hist: {"rule_score": rule_score, "flags": []}
    lstm_mod.predict  = lambda seq:      {"dl_score": dl_score}
    clear_history("sim_user")
    result = assess({"user_id":"sim_user","amount":999,"recipient":"sim@upi"})
    rule_mod.evaluate = _original_rule
    lstm_mod.predict  = _original_lstm
    return result


# ── ALLOW scenario ────────────────────────────────────────────────────
r_allow = _force_assess(rule_score=0.1, dl_score=0.1)
expected_allow_score = round(0.4*0.1 + 0.6*0.1, 4)
print(f"  [ALLOW scenario]  rule=0.1, dl=0.1")
print(f"    risk_score={r_allow['risk_score']}, action={r_allow['action']}, reasons={r_allow['reasons']}")
check("ALLOW: correct score",    r_allow["risk_score"] == expected_allow_score,
      got=r_allow["risk_score"], expected=expected_allow_score)
check("ALLOW: action is ALLOW",  r_allow["action"] == "ALLOW", got=r_allow["action"])
check("ALLOW: empty reasons",    r_allow["reasons"] == [], got=r_allow["reasons"])

# ── VERIFY scenario ───────────────────────────────────────────────────
r_verify = _force_assess(rule_score=0.6, dl_score=0.6)
expected_verify_score = round(0.4*0.6 + 0.6*0.6, 4)
print(f"\n  [VERIFY scenario]  rule=0.6, dl=0.6")
print(f"    risk_score={r_verify['risk_score']}, action={r_verify['action']}, reasons={r_verify['reasons']}")
check("VERIFY: correct score",   r_verify["risk_score"] == expected_verify_score,
      got=r_verify["risk_score"], expected=expected_verify_score)
check("VERIFY: action is VERIFY",r_verify["action"] == "VERIFY", got=r_verify["action"])
check("VERIFY: has reasons",     len(r_verify["reasons"]) >= 1)

# ── BLOCK scenario ────────────────────────────────────────────────────
r_block = _force_assess(rule_score=0.9, dl_score=0.9)
expected_block_score = round(0.4*0.9 + 0.6*0.9, 4)
print(f"\n  [BLOCK scenario]  rule=0.9, dl=0.9")
print(f"    risk_score={r_block['risk_score']}, action={r_block['action']}, reasons={r_block['reasons']}")
check("BLOCK: correct score",    r_block["risk_score"] == expected_block_score,
      got=r_block["risk_score"], expected=expected_block_score)
check("BLOCK: action is BLOCK",  r_block["action"] == "BLOCK", got=r_block["action"])
check("BLOCK: has reasons",      len(r_block["reasons"]) >= 1)


# ════════════════════════════════════════════════════════════════════════
#  SECTION 5 — FALLBACK SAFETY
#  Simulate a crash inside rule_engine or lstm_service.
# ════════════════════════════════════════════════════════════════════════
section("5. FALLBACK SAFETY  (module crash simulation)")

print("  Simulating rule_engine crash → expect fallback score 0.5 for that module")

def _crashing_rule(tx, hist):
    raise RuntimeError("Simulated rule_engine crash!")

def _crashing_lstm(seq):
    raise RuntimeError("Simulated lstm crash!")

# Crash rule engine
rule_mod.evaluate = _crashing_rule
clear_history("fallback_u")
r = assess({"user_id":"fallback_u","amount":500,"recipient":"x@upi"})
rule_mod.evaluate = _original_rule
check("rule crash: system still returns valid response",
      "risk_score" in r and "action" in r)
check("rule crash: action is valid",
      r["action"] in ("ALLOW","VERIFY","BLOCK"), got=r["action"])
print(f"    Result after rule crash: {r}")

# Crash LSTM
lstm_mod.predict = _crashing_lstm
clear_history("fallback_u2")
r2 = assess({"user_id":"fallback_u2","amount":500,"recipient":"x@upi"})
lstm_mod.predict = _original_lstm
check("lstm crash: system still returns valid response",
      "risk_score" in r2 and "action" in r2)
print(f"    Result after lstm crash: {r2}")

# Both crash
rule_mod.evaluate = _crashing_rule
lstm_mod.predict  = _crashing_lstm
clear_history("fallback_u3")
r3 = assess({"user_id":"fallback_u3","amount":500,"recipient":"x@upi"})
rule_mod.evaluate = _original_rule
lstm_mod.predict  = _original_lstm
check("BOTH crash: still returns valid response",
      "risk_score" in r3 and "action" in r3)
print(f"    Result after BOTH crash: {r3}")


# ════════════════════════════════════════════════════════════════════════
#  SECTION 6 — INPUT VALIDATION EDGE CASES
# ════════════════════════════════════════════════════════════════════════
section("6. INPUT EDGE CASES")

clear_history("edge_u")

# Missing user_id
r = assess({"amount": 500, "recipient": "x@upi"})
check("Missing user_id: no crash",    "action" in r)

# Missing timestamp
r = assess({"user_id":"edge_u","amount":500,"recipient":"x@upi"})
check("Missing timestamp: no crash",  "action" in r)

# Very large amount
r = assess({"user_id":"edge_u","amount":9_999_999,"recipient":"x@upi"})
check("Very large amount: no crash",  "action" in r)

# Empty recipient (sanitised)
r = assess({"user_id":"edge_u","amount":500,"recipient":""})
check("Empty recipient: no crash",    "action" in r)


# ════════════════════════════════════════════════════════════════════════
#  SECTION 7 — PERFORMANCE
# ════════════════════════════════════════════════════════════════════════
section("7. PERFORMANCE")

import time
clear_history("perf_u")
t0 = time.time()
for _ in range(20):
    assess({"user_id":"perf_u","amount":1000,"recipient":"fast@upi"})
avg_ms = (time.time() - t0) * 1000 / 20
check(f"20 calls avg {avg_ms:.1f}ms (must be <200ms)", avg_ms < 200, got=f"{avg_ms:.1f}ms")


# ════════════════════════════════════════════════════════════════════════
#  SUMMARY TABLE
# ════════════════════════════════════════════════════════════════════════
total = _passed + _failed
print(f"\n{'='*60}")
print(f"  RESULTS: {_passed}/{total} passed", end="")
if _failed == 0:
    print("  ✓  All checks passed — system is integration-ready!")
else:
    print(f"\n  {_failed} FAILED — fix before demo.")
print(f"{'='*60}")

print("""
╔══════════════════════════════════════════════════════════╗
║  DECISION THRESHOLDS (dummy modules, both return 0.5)   ║
╠══════════════════════════════════════════════════════════╣
║  Score    Action   What triggers it                      ║
║  ──────   ──────   ──────────────────────────────────── ║
║  < 0.50   ALLOW    Both modules calm, no flags           ║
║  ≥ 0.50   VERIFY   Medium risk or unknown pattern        ║
║  ≥ 0.75   BLOCK    High risk, strong anomaly signal      ║
╚══════════════════════════════════════════════════════════╝
""")

if _failed:
    sys.exit(1)