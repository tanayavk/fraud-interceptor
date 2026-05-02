# backend/db/database.py
"""
In-Memory Transaction Store
Stores the last 5 transactions per user.
"""
from collections import deque

_MAX_HISTORY = 5
_store: dict = {}  # { user_id: deque[dict] }


def get_history(user_id: str) -> list:
    """Returns ordered list of past transactions for user. Empty list if none."""
    return list(_store.get(user_id, []))


def append_transaction(user_id: str, transaction: dict) -> None:
    """Appends a transaction. Auto-evicts oldest when window > 5."""
    if user_id not in _store:
        _store[user_id] = deque(maxlen=_MAX_HISTORY)
    _store[user_id].append(transaction)


def clear_history(user_id: str) -> None:
    """Clears all history for a user. Used in tests."""
    if user_id in _store:
        del _store[user_id]