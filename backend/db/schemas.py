# backend/db/schemas.py
"""
Data shape reference — not imported by any module.
Describes the shape of dicts passed around the system.
"""
TRANSACTION_SCHEMA = {
    "user_id":   "str",
    "amount":    "float",
    "recipient": "str",
    "timestamp": "float",
    "device_id": "str",
}
HISTORY_ENTRY_SCHEMA = TRANSACTION_SCHEMA