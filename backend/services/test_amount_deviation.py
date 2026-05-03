from rule_engine_only import evaluate

# Test Amount Deviation Rule
transaction = {
    "amount": 1000.0,
    "recipient": "test@upi",
    "timestamp": 1672531200,
    "device_id": "dev1"
}

history = [
    {"amount": 100.0, "recipient": "test@upi", "timestamp": 1672444800},
    {"amount": 95.0, "recipient": "test@upi", "timestamp": 1672358400},
]

result = evaluate(transaction, history)

print(f"Rule Score: {result['rule_score']}")
print(f"Flags: {result['flags']}")

# Expected: rule_score = 0.3, flags = ['high_amount_deviation']
assert result['rule_score'] == 0.5
assert 'high_amount_deviation' in result['flags']
print("✓ Amount Deviation Rule PASSED")


from rule_engine_only import evaluate
from datetime import datetime

# Test odd hour (3 AM UTC)
now_utc = datetime.utcnow()
odd_hour_ts = int(now_utc.replace(hour=3, minute=0, second=0).timestamp())

transaction = {
    "amount": 100.0,
    "recipient": "test@upi",
    "timestamp": odd_hour_ts,
    "device_id": "dev1"
}

result = evaluate(transaction, [])
print(f"Result: {result}")
# If current UTC time is not between 2-5 AM, rule won't trigger
# To force test: use a fixed timestamp like 1672499000

from rule_engine_only import evaluate

# Test: Amount exactly at 3× threshold (should NOT trigger)
avg_amount = 100.0
boundary_amount = avg_amount * 3.0

transaction = {
    "amount": boundary_amount,
    "recipient": "test@upi",
    "timestamp": 1672531200
}

history = [
    {"amount": avg_amount, "timestamp": 1672444800},
    {"amount": avg_amount, "timestamp": 1672358400},
    {"amount": avg_amount, "timestamp": 1672272000},
]

result = evaluate(transaction, history)
print(f"Boundary test (3.0×): {result}")
# Expected: 'high_amount_deviation' NOT in flags (rule uses > not >=)

# Test: Amount just over threshold (should trigger)
transaction["amount"] = boundary_amount + 1
result = evaluate(transaction, history)
print(f"Boundary test (3.01×): {result}")
# Expected: 'high_amount_deviation' in flags

from rule_engine_only import evaluate

# Test 1: None input
result = evaluate(None, [])
print(f"None transaction: {result}")
assert result['rule_score'] == 0.0
assert result['flags'] == []

# Test 2: Invalid type
result = evaluate("not a dict", [])
print(f"String transaction: {result}")
assert result['rule_score'] == 0.0

# Test 3: Missing required fields
result = evaluate({"amount": 100}, [])
print(f"Missing fields: {result}")
assert result['rule_score'] == 0.0

# Test 4: Invalid field types
result = evaluate({
    "amount": "not a number",
    "recipient": 123,
    "timestamp": "not a timestamp"
}, [])
print(f"Invalid types: {result}")
assert result['rule_score'] == 0.2

print("✓ All error handling tests PASSED")

from rule_engine_only import evaluate

# Test 1: None input
result = evaluate(None, [])
print(f"None transaction: {result}")
assert result['rule_score'] == 0.0
assert result['flags'] == []

# Test 2: Invalid type
result = evaluate("not a dict", [])
print(f"String transaction: {result}")
assert result['rule_score'] == 0.0

# Test 3: Missing required fields
result = evaluate({"amount": 100}, [])
print(f"Missing fields: {result}")
assert result['rule_score'] == 0.0

# Test 4: Invalid field types
result = evaluate({
    "amount": "not a number",
    "recipient": 123,
    "timestamp": "not a timestamp"
}, [])
print(f"Invalid types: {result}")
assert result['rule_score'] == 0.2

print("✓ All error handling tests PASSED")

from rule_engine_only import RuleEngine

engine = RuleEngine()
transaction = {"amount": 5000.0, "recipient": "test@upi", "timestamp": 1672531200}
history = [{"amount": 100.0, "recipient": "test@upi", "timestamp": 1672444800}]

# Get detailed result
result = engine.evaluate(transaction, history)
print(f"Rule Score: {result['rule_score']}")
print(f"Flags: {result['flags']}")

# Check average calculation
amounts = [tx.get('amount', 0) for tx in history]
avg = sum(amounts) / len(amounts)
print(f"Average: {avg}, Threshold: {avg * 3}")
print(f"Current amount: {transaction['amount']}")
print(f"Should trigger: {transaction['amount'] > avg * 3}")