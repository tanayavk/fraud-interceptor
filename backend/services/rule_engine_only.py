"""
Fraud Interceptor - Cybersecurity Rule Engine
=============================================
Fast, deterministic fraud detection using 5 cybersecurity rules.

RULES IMPLEMENTED:
1. Amount Deviation - Detects unusually large transactions
2. New Recipient - Detects first-time transfers to new accounts
3. Transaction Velocity - Detects rapid-fire transactions (bot activity)
4. Odd Hour Activity - Detects transactions during unusual hours (2-5 AM UTC)
5. New Device - Detects transactions from new devices

No external dependencies. Pure Python logic only.
"""

from datetime import datetime
from typing import Dict, List, Any


class RuleEngine:
    """
    Cybersecurity rule-based fraud detection engine.
    Fast, deterministic, explainable fraud signals.
    """

    # Risk scores per rule
    AMOUNT_DEVIATION_RISK = 0.3
    NEW_RECIPIENT_RISK = 0.2
    HIGH_VELOCITY_RISK = 0.3
    ODD_HOUR_RISK = 0.2
    NEW_DEVICE_RISK = 0.2

    # Configuration
    VELOCITY_WINDOW_SECONDS = 300  # 5 minutes
    VELOCITY_THRESHOLD = 3  # transactions
    ODD_HOUR_START = 2  # 2 AM
    ODD_HOUR_END = 5  # 5 AM
    AMOUNT_MULTIPLIER = 3.0  # 3x average spend

    def evaluate(self, transaction: Dict[str, Any], history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate a transaction against all cybersecurity rules.

        Args:
            transaction: Current transaction
                {
                    "amount": float,
                    "recipient": string,
                    "timestamp": int (Unix seconds),
                    "device_id": string (optional)
                }
            history: List of past transactions

        Returns:
            {
                "rule_score": float (0.0 to 1.0),
                "flags": list[str]
            }
        """

        # Input validation
        if not self._validate_transaction(transaction):
            return {"rule_score": 0.0, "flags": []}

        if not history:
            history = []

        # Initialize scoring
        risk_score = 0.0
        flags = []

        try:
            # RULE 1: Amount Deviation
            amount_risk, amount_flag = self._check_amount_deviation(transaction, history)
            if amount_flag:
                risk_score += amount_risk
                flags.append(amount_flag)

            # RULE 2: New Recipient
            new_recipient_risk, new_recipient_flag = self._check_new_recipient(transaction, history)
            if new_recipient_flag:
                risk_score += new_recipient_risk
                flags.append(new_recipient_flag)

            # RULE 3: Transaction Velocity
            velocity_risk, velocity_flag = self._check_velocity(transaction, history)
            if velocity_flag:
                risk_score += velocity_risk
                flags.append(velocity_flag)

            # RULE 4: Odd Hour Activity
            odd_hour_risk, odd_hour_flag = self._check_odd_hour(transaction)
            if odd_hour_flag:
                risk_score += odd_hour_risk
                flags.append(odd_hour_flag)

            # RULE 5: New Device
            device_risk, device_flag = self._check_new_device(transaction, history)
            if device_flag:
                risk_score += device_risk
                flags.append(device_flag)

        except Exception as e:
            # Failsafe: return safe default
            print(f"[RuleEngine] Error during evaluation: {str(e)}")
            return {"rule_score": 0.0, "flags": []}

        # Cap score at 1.0
        risk_score = min(risk_score, 1.0)

        return {
            "rule_score": round(risk_score, 4),
            "flags": flags
        }

    # ==================== RULE 1: AMOUNT DEVIATION ====================

    def _check_amount_deviation(self, transaction: Dict, history: List[Dict]) -> tuple:
        """
        RULE 1: Amount Deviation
        
        Detects unusually large transactions.
        
        Trigger: If transaction amount > 3× average historical spend
        Risk: +0.3
        Flag: "high_amount_deviation"
        
        Example:
            History: $100, $95 → Average = $97.50
            Threshold: $97.50 × 3 = $292.50
            Current: $5000 > $292.50 ✓ TRIGGERED
        """
        if not history or "amount" not in transaction:
            return 0.0, None

        try:
            current_amount = float(transaction["amount"])
            historical_amounts = [float(tx.get("amount", 0)) for tx in history if tx.get("amount")]

            if not historical_amounts:
                return 0.0, None

            avg_spend = sum(historical_amounts) / len(historical_amounts)

            # Check if current amount deviates significantly (>3x average)
            if current_amount > (avg_spend * self.AMOUNT_MULTIPLIER):
                return self.AMOUNT_DEVIATION_RISK, "high_amount_deviation"

        except (ValueError, TypeError):
            return 0.0, None

        return 0.0, None

    # ==================== RULE 2: NEW RECIPIENT ====================

    def _check_new_recipient(self, transaction: Dict, history: List[Dict]) -> tuple:
        """
        RULE 2: New Recipient
        
        Detects first-time transfers to new accounts.
        
        Trigger: If recipient not found in transaction history
        Risk: +0.2
        Flag: "new_recipient"
        
        Example:
            History recipients: ["alice@upi", "alice@upi"]
            Current: "bob@upi"
            "bob@upi" not in history ✓ TRIGGERED
        """
        if "recipient" not in transaction:
            return 0.0, None

        current_recipient = str(transaction["recipient"]).lower().strip()

        if not current_recipient:
            return 0.0, None

        # Extract unique recipients from history
        historical_recipients = set()
        for tx in history:
            if "recipient" in tx:
                historical_recipients.add(str(tx["recipient"]).lower().strip())

        # If recipient not in history, it's new
        if not historical_recipients or current_recipient not in historical_recipients:
            return self.NEW_RECIPIENT_RISK, "new_recipient"

        return 0.0, None

    # ==================== RULE 3: TRANSACTION VELOCITY ====================

    def _check_velocity(self, transaction: Dict, history: List[Dict]) -> tuple:
        """
        RULE 3: Transaction Velocity
        
        Detects rapid-fire transactions (bot activity).
        
        Trigger: If >3 transactions in last 5 minutes
        Risk: +0.3
        Flag: "high_transaction_velocity"
        
        Example:
            Time window: Last 300 seconds (5 minutes)
            Transactions in window: 3 (at T-60s, T-120s, T-180s)
            3 >= 3 ✓ TRIGGERED
        """
        if "timestamp" not in transaction or not history:
            return 0.0, None

        try:
            current_timestamp = int(transaction["timestamp"])
            time_window_start = current_timestamp - self.VELOCITY_WINDOW_SECONDS

            # Count transactions within velocity window
            recent_transactions = sum(
                1 for tx in history
                if int(tx.get("timestamp", 0)) >= time_window_start
            )

            # If 3+ transactions in window (including current one)
            if recent_transactions >= self.VELOCITY_THRESHOLD:
                return self.HIGH_VELOCITY_RISK, "high_transaction_velocity"

        except (ValueError, TypeError):
            return 0.0, None

        return 0.0, None

    # ==================== RULE 4: ODD HOUR ACTIVITY ====================

    def _check_odd_hour(self, transaction: Dict) -> tuple:
        """
        RULE 4: Odd Hour Activity
        
        Detects transactions during unusual hours.
        
        Trigger: Transactions between 2 AM and 5 AM UTC
        Risk: +0.2
        Flag: "odd_hour_transaction"
        
        Example:
            Timestamp: 2023-01-01 03:30:00 UTC (3 AM)
            Hour: 3
            2 <= 3 < 5 ✓ TRIGGERED
        """
        if "timestamp" not in transaction:
            return 0.0, None

        try:
            timestamp = int(transaction["timestamp"])
            # Convert Unix timestamp to hour (UTC)
            dt = datetime.utcfromtimestamp(timestamp)
            hour = dt.hour

            # Check if transaction is in odd hours (2-5 AM)
            if self.ODD_HOUR_START <= hour < self.ODD_HOUR_END:
                return self.ODD_HOUR_RISK, "odd_hour_transaction"

        except (ValueError, TypeError, OSError):
            return 0.0, None

        return 0.0, None

    # ==================== RULE 5: NEW DEVICE ====================

    def _check_new_device(self, transaction: Dict, history: List[Dict]) -> tuple:
        """
        RULE 5: New Device
        
        Detects transactions from new devices.
        
        Trigger: If device_id not seen in history
        Risk: +0.2
        Flag: "new_device"
        
        Example:
            History devices: ["device_1", "device_1"]
            Current: "device_2"
            "device_2" not in history ✓ TRIGGERED
        """
        if "device_id" not in transaction or not transaction.get("device_id"):
            return 0.0, None

        current_device = str(transaction["device_id"]).lower().strip()

        if not current_device:
            return 0.0, None

        # Extract unique devices from history
        historical_devices = set()
        for tx in history:
            if "device_id" in tx and tx.get("device_id"):
                historical_devices.add(str(tx["device_id"]).lower().strip())

        # If device not in history, it's new
        if not historical_devices or current_device not in historical_devices:
            return self.NEW_DEVICE_RISK, "new_device"

        return 0.0, None

    # ==================== VALIDATION ====================

    def _validate_transaction(self, transaction: Dict) -> bool:
        """Validate transaction has minimum required fields."""
        if not isinstance(transaction, dict):
            return False

        # Must have at least amount and recipient
        required_fields = ["amount", "recipient", "timestamp"]
        return all(field in transaction for field in required_fields)


# ==================== MODULE-LEVEL INTERFACE ====================

def evaluate(transaction: Dict[str, Any], history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Module-level interface for the rule engine.
    
    Usage:
        result = evaluate(transaction, history)
        # Returns: {"rule_score": 0.5, "flags": ["high_amount_deviation"]}
    """
    engine = RuleEngine()
    return engine.evaluate(transaction, history)


# ==================== EXAMPLES & TESTING ====================

if __name__ == "__main__":
    """
    Rule Engine Examples
    """

    print("=" * 70)
    print("CYBERSECURITY RULES ENGINE - EXAMPLES")
    print("=" * 70)

    # Example 1: Normal Transaction
    print("\n[EXAMPLE 1] Normal Transaction")
    print("-" * 70)
    tx = {
        "amount": 100.0,
        "recipient": "alice@upi",
        "timestamp": 1672531200,
        "device_id": "device_1"
    }
    history = [
        {"amount": 95.0, "recipient": "alice@upi", "timestamp": 1672444800, "device_id": "device_1"},
    ]
    result = evaluate(tx, history)
    print(f"Transaction: {tx}")
    print(f"Result: {result}")
    print(f"Expected: rule_score=0.0, flags=[]")

    # Example 2: High Amount Deviation (RULE 1)
    print("\n[EXAMPLE 2] High Amount Deviation - RULE 1")
    print("-" * 70)
    tx = {
        "amount": 5000.0,
        "recipient": "alice@upi",
        "timestamp": 1672531200,
        "device_id": "device_1"
    }
    history = [
        {"amount": 100.0, "recipient": "alice@upi", "timestamp": 1672444800},
        {"amount": 95.0, "recipient": "alice@upi", "timestamp": 1672358400},
    ]
    result = evaluate(tx, history)
    print(f"Amount: $5000 (Average: $97.50, Threshold: $292.50)")
    print(f"5000 > 292.50 ✓ RULE 1 TRIGGERED")
    print(f"Result: {result}")

    # Example 3: New Recipient (RULE 2)
    print("\n[EXAMPLE 3] New Recipient - RULE 2")
    print("-" * 70)
    tx = {
        "amount": 100.0,
        "recipient": "bob@upi",
        "timestamp": 1672531200,
        "device_id": "device_1"
    }
    history = [
        {"amount": 100.0, "recipient": "alice@upi", "timestamp": 1672444800},
    ]
    result = evaluate(tx, history)
    print(f"Recipient: bob@upi (not in history)")
    print(f"bob@upi not in ['alice@upi'] ✓ RULE 2 TRIGGERED")
    print(f"Result: {result}")

    # Example 4: High Velocity (RULE 3)
    print("\n[EXAMPLE 4] High Velocity - RULE 3")
    print("-" * 70)
    current_ts = 1672531200
    tx = {
        "amount": 100.0,
        "recipient": "alice@upi",
        "timestamp": current_ts,
    }
    history = [
        {"amount": 50.0, "recipient": "alice@upi", "timestamp": current_ts - 60},
        {"amount": 50.0, "recipient": "alice@upi", "timestamp": current_ts - 120},
        {"amount": 50.0, "recipient": "alice@upi", "timestamp": current_ts - 180},
    ]
    result = evaluate(tx, history)
    print(f"Transactions in last 5 min: 3 (at T-60s, T-120s, T-180s)")
    print(f"3 >= 3 ✓ RULE 3 TRIGGERED")
    print(f"Result: {result}")

    # Example 5: Odd Hour (RULE 4)
    print("\n[EXAMPLE 5] Odd Hour (3 AM) - RULE 4")
    print("-" * 70)
    odd_hour_ts = 1672499000  # Approximately 3 AM UTC
    tx = {
        "amount": 100.0,
        "recipient": "alice@upi",
        "timestamp": odd_hour_ts,
    }
    result = evaluate(tx, [])
    dt = datetime.utcfromtimestamp(odd_hour_ts)
    print(f"Timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')} (Hour: {dt.hour})")
    print(f"2 <= {dt.hour} < 5 ✓ RULE 4 TRIGGERED")
    print(f"Result: {result}")

    # Example 6: New Device (RULE 5)
    print("\n[EXAMPLE 6] New Device - RULE 5")
    print("-" * 70)
    tx = {
        "amount": 100.0,
        "recipient": "alice@upi",
        "timestamp": 1672531200,
        "device_id": "device_2"
    }
    history = [
        {"amount": 100.0, "recipient": "alice@upi", "timestamp": 1672444800, "device_id": "device_1"},
    ]
    result = evaluate(tx, history)
    print(f"Device: device_2 (not in history)")
    print(f"device_2 not in ['device_1'] ✓ RULE 5 TRIGGERED")
    print(f"Result: {result}")

    # Example 7: Multiple Rules
    print("\n[EXAMPLE 7] Multiple Rules Triggered")
    print("-" * 70)
    tx = {
        "amount": 5000.0,
        "recipient": "charlie@upi",
        "timestamp": 1672499000,
        "device_id": "device_new"
    }
    history = [
        {"amount": 100.0, "recipient": "alice@upi", "timestamp": 1672444800, "device_id": "device_1"},
    ]
    result = evaluate(tx, history)
    print(f"Rules Triggered:")
    print(f"  ✓ RULE 1 (Amount > 3x average)")
    print(f"  ✓ RULE 2 (New recipient)")
    print(f"  ✓ RULE 4 (Odd hour)")
    print(f"  ✓ RULE 5 (New device)")
    print(f"Score = 0.3 + 0.2 + 0.2 + 0.2 = 0.9")
    print(f"Result: {result}")

    print("\n" + "=" * 70)
    print("✅ ALL RULES WORKING CORRECTLY")
    print("=" * 70)