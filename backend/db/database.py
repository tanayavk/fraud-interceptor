# # backend/db/database.py
# """
# In-Memory Transaction Store
# Stores the last 5 transactions per user.
# """
# from collections import deque

# _MAX_HISTORY = 5
# _store: dict = {}  # { user_id: deque[dict] }


# def get_history(user_id: str) -> list:
#     """Returns ordered list of past transactions for user. Empty list if none."""
#     return list(_store.get(user_id, []))


# def append_transaction(user_id: str, transaction: dict) -> None:
#     """Appends a transaction. Auto-evicts oldest when window > 5."""
#     if user_id not in _store:
#         _store[user_id] = deque(maxlen=_MAX_HISTORY)
#     _store[user_id].append(transaction)


# def clear_history(user_id: str) -> None:
#     """Clears all history for a user. Used in tests."""
#     if user_id in _store:
#         del _store[user_id]


import json
import os
from collections import deque

# File where history will be saved
HISTORY_FILE = "transaction_history.json"
_MAX_HISTORY = 5

def _load_data():
    """Loads the entire history dictionary from the JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {}

def _save_data(data):
    """Saves the history dictionary back to the JSON file."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_history(user_id: str) -> list:
    """Returns the last 5 transactions for a user from the JSON file."""
    db = _load_data()
    # Returns the list or an empty list if user doesn't exist
    return db.get(user_id, [])

def append_transaction(user_id: str, transaction: dict) -> None:
    """Appends a transaction and ensures only the last 5 are kept on disk."""
    db = _load_data()
    
    if user_id not in db:
        db[user_id] = []
    
    # Add new transaction
    db[user_id].append(transaction)
    
    # Maintain the 5-transaction window
    if len(db[user_id]) > _MAX_HISTORY:
        db[user_id] = db[user_id][-_MAX_HISTORY:]
    
    _save_data(db)

def clear_history(user_id: str) -> None:
    """Removes a user's history from the JSON file."""
    db = _load_data()
    if user_id in db:
        del db[user_id]
        _save_data(db)