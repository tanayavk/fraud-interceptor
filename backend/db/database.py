# backend/db/database.py
"""
Persistent Transaction Store
============================
Thread-safe JSON file I/O.
Stores exactly the last 5 transactions per user.

The file is read fresh on every call so multiple processes / test
runs always see consistent state.  Writes apply a strict trailing
slice before serialisation so the cap is enforced atomically.
"""

import json
import os
import threading

# ── Path resolution ──────────────────────────────────────────────────────────
# Always resolve relative to the *project root* (two levels above this file),
# so the server can be launched from any working directory.
_HERE        = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))   # …/fraud-intercepter
HISTORY_FILE  = os.path.join(_PROJECT_ROOT, "transaction_history.json")

_MAX_HISTORY = 5
_lock        = threading.Lock()   # serialise concurrent writes


# ── Internal helpers ─────────────────────────────────────────────────────────

def _load_data() -> dict:
    """
    Reads the JSON file and returns the full history dictionary.
    Returns an empty dict on missing file or any parse error —
    never raises.
    """
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            # Defensive: top-level must be a dict
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError, ValueError):
        return {}


def _save_data(data: dict) -> None:
    """Writes the history dictionary back to the JSON file."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=4, default=str)


# ── Public API ───────────────────────────────────────────────────────────────

def get_history(user_id: str) -> list:
    """
    Returns the last ≤5 transactions for *user_id*.
    Returns an empty list if the user has no history.
    Never raises.
    """
    if not user_id:
        return []
    db = _load_data()
    history = db.get(str(user_id), [])
    # Guarantee list type even if the JSON was hand-edited
    if not isinstance(history, list):
        return []
    return history[-_MAX_HISTORY:]


def append_transaction(user_id: str, transaction: dict) -> None:
    """
    Appends *transaction* to *user_id*'s history and persists it.
    Enforces the 5-record cap with a strict trailing slice.
    Thread-safe via a module-level lock.
    """
    if not user_id or not isinstance(transaction, dict):
        return

    with _lock:
        db = _load_data()
        uid = str(user_id)

        if uid not in db or not isinstance(db[uid], list):
            db[uid] = []

        db[uid].append(transaction)
        # Strict cap — always keep only the most recent 5
        db[uid] = db[uid][-_MAX_HISTORY:]

        _save_data(db)


def clear_history(user_id: str) -> None:
    """Removes all history for *user_id*. Used in tests / manual resets."""
    if not user_id:
        return
    with _lock:
        db = _load_data()
        uid = str(user_id)
        if uid in db:
            del db[uid]
            _save_data(db)