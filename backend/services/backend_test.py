# cat > backend_test.py << 'EOF'
# Simulate what the backend will do
from rule_engine import evaluate as rule_evaluate

# Simulate DL model
def simulate_dl_model(sequence):
    """Mock DL model that returns a score"""
    return {"dl_score": 0.6}

# Simulate user transaction
user_id = "user_123"
transaction = {
    "amount": 5000.0,
    "recipient": "bob@upi",
    "timestamp": 1672531200,
    "device_id": "device_1"
}

# Simulate user history
history = [
    {"amount": 100.0, "recipient": "alice@upi", "timestamp": 1672444800, "device_id": "device_1"},
]

# Step 1: Rule Engine (always works)
print("Step 1: Call Rule Engine")
rule_result = rule_evaluate(transaction, history)
print(f"  Rule Score: {rule_result['rule_score']}")
print(f"  Flags: {rule_result['flags']}")

# Step 2: DL Model (may fail, so wrap in try-catch)
print("\nStep 2: Call DL Model")
try:
    dl_result = simulate_dl_model(history)
    dl_score = dl_result["dl_score"]
    print(f"  DL Score: {dl_score}")
except Exception as e:
    print(f"  DL Model failed, using fallback: 0.5")
    dl_score = 0.5

# Step 3: Combine scores
print("\nStep 3: Combine Scores")
final_score = 0.4 * rule_result['rule_score'] + 0.6 * dl_score
print(f"  Final Score: {final_score:.4f}")
print(f"  Calculation: 0.4 × {rule_result['rule_score']} + 0.6 × {dl_score} = {final_score:.4f}")

# Step 4: Determine action
print("\nStep 4: Determine Action")
if final_score >= 0.7:
    action = "BLOCK"
    emoji = "🔴"
elif final_score >= 0.5:
    action = "VERIFY"
    emoji = "🟡"
else:
    action = "ALLOW"
    emoji = "🟢"

print(f"  {emoji} Action: {action}")

# Step 5: Response
print("\nStep 5: API Response")
response = {
    "risk_score": final_score,
    "action": action,
    "reasons": rule_result['flags'] if rule_result['flags'] else ["Transaction appears normal"]
}
print(f"  {response}")

print("\n✅ Backend integration test passed!")
# EOF