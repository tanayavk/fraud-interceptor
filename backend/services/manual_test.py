# cat > manual_test.py << 'EOF'
from rule_engine import evaluate

# Test 1: Normal transaction
print("=" * 50)
print("TEST 1: Normal Transaction")
print("=" * 50)
tx = {
    "amount": 100.0,
    "recipient": "alice@upi",
    "timestamp": 1672531200,
    "device_id": "device_1"
}
history = [
    {"amount": 95.0, "recipient": "alice@upi", "timestamp": 1672444800, "device_id": "device_1"},
    {"amount": 110.0, "recipient": "alice@upi", "timestamp": 1672358400, "device_id": "device_1"},
]
result = evaluate(tx, history)
print(f"Result: {result}")
assert result['rule_score'] == 0.0, f"Expected 0.0, got {result['rule_score']}"
assert result['flags'] == [], f"Expected [], got {result['flags']}"
print("✓ PASSED\n")

# Test 2: Large amount
print("=" * 50)
print("TEST 2: Large Amount (Deviation)")
print("=" * 50)
tx = {
    "amount": 5000.0,
    "recipient": "alice@upi",
    "timestamp": 1672531200
}
history = [
    {"amount": 100.0, "recipient": "alice@upi", "timestamp": 1672444800},
    {"amount": 95.0, "recipient": "alice@upi", "timestamp": 1672358400},
]
result = evaluate(tx, history)
print(f"Result: {result}")
assert result['rule_score'] == 0.3, f"Expected 0.3, got {result['rule_score']}"
assert 'high_amount_deviation' in result['flags']
print("✓ PASSED\n")

# Test 3: Error handling
print("=" * 50)
print("TEST 3: Invalid Input (Failsafe)")
print("=" * 50)
result = evaluate({}, [])
print(f"Result: {result}")
assert result['rule_score'] == 0.0
assert result['flags'] == []
print("✓ PASSED\n")

print("=" * 50)
print("✅ ALL MANUAL TESTS PASSED")
print("=" * 50)
# EOF