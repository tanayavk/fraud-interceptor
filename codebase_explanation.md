# Fraud Interceptor — Complete Codebase Explanation (Beginner Level)

> **What is this project?**
> A system that watches when you click "Pay Now" on a fake bank website, secretly checks whether the transaction looks fraudulent, and then either ALLOWS it, asks for OTP verification, or BLOCKS it — all before the money moves.

---

## 🗂 Project Structure Overview

```
fraud-intercepter/
├── backend/          ← Python server (the brain)
├── extension/        ← Chrome browser extension (the watcher)
├── mock-bank/        ← Fake bank website (the UI demo)
├── ml/               ← Machine learning model training files
├── requirements.txt  ← Python packages needed
└── transaction_history.json  ← Where past transactions are saved
```

Think of it like a security guard system at a bank:
- **mock-bank** = the bank's counter where you fill out forms
- **extension** = a hidden security camera watching you fill the form
- **backend** = the security HQ that analyzes whether you're suspicious
- **ml/** = where the AI "brain" was trained

---

## 🏦 LAYER 1 — The Mock Bank Website (`mock-bank/`)

These 3 files together create a fake bank you open in Chrome.

---

### `mock-bank/index.html` — The Web Page Structure

**What it is:** The HTML skeleton — every button, input box, and modal popup is defined here. The browser reads this and draws the page.

**Key sections:**

| HTML Section | What it does |
|---|---|
| `#screen-dashboard` | The main banking page the user sees |
| `#pay-form` | The payment form with `#recipient` and `#amount` inputs |
| `#pay-btn` | The "Pay Now" button — **this is intercepted by the extension** |
| `#otp-overlay` | A hidden popup that appears when risk = VERIFY |
| `#block-overlay` | A hidden popup that appears when risk = BLOCK |
| `#allow-overlay` | A hidden popup that appears when risk = ALLOW |
| `#success-overlay` | A receipt popup shown after OTP is entered correctly |

**Important:** All these popups start with `class="overlay hidden"`. The word `hidden` makes them invisible. `script.js` removes the word `hidden` to show them.

**The critical hook (line 181–191):**
```html
<!-- The extension intercepts this button's click at capture phase -->
<button type="submit" id="pay-btn">Pay Now</button>
```
This comment tells you: the Chrome extension grabs this button BEFORE the normal form submit fires.

---

### `mock-bank/script.js` — The Bank's Brain (UI Logic)

**What it is:** 783 lines of JavaScript that make the bank page interactive. It handles everything from tab-switching to showing the OTP popup.

**Key concepts for beginners:**

**`window.fraudInterceptorReady = true` (line 741)**
This is a flag — like putting up a sign that says "I'm here!". The Chrome extension checks for this flag. If it's `true`, the extension knows this page has script.js loaded and will hand off control to it.

**The two ways a transaction gets assessed:**

**Path A — Extension is installed:**
1. User clicks Pay Now
2. Extension intercepts the click (`content.js` runs first)
3. Extension calls backend, gets risk result
4. Extension fires a custom browser event: `document.dispatchEvent(new CustomEvent('fraudResult', { detail: riskData }))`
5. `script.js` listens for this event (line 747) and calls `routeResponse()`

**Path B — No extension:**
1. User clicks Pay Now → form submits normally
2. `script.js`'s own submit listener fires (line 295)
3. It calls the backend directly with `fetch()`
4. Gets risk result and calls `routeResponse()`

**`routeResponse()` function (line 363):**
```javascript
function routeResponse(data, amount, recipient) {
  if      (action === 'ALLOW')  handleAllow(...)
  else if (action === 'VERIFY') handleVerify(...)
  else                          handleBlock(...)
}
```
This is the traffic cop. Based on what the backend says, it sends the user to one of 3 outcomes.

**`handleAllow()` (line 373):**
Shows the green "Transaction Approved" popup. User must click "Proceed" to actually complete the transfer.

**`handleVerify()` (line 396):**
- Generates a random 6-digit OTP: `Math.floor(100000 + Math.random() * 900000)`
- Shows it in a fake SMS preview on screen
- Shows the OTP input boxes
- Starts a 2-minute countdown timer
- User must type the correct OTP to proceed

**`handleBlock()` (line 444):**
Shows the red "Transaction Blocked" popup with a risk percentage bar. The only button is "Understood — Go Back". Money does NOT move.

**`completeTransaction()` (line 659):**
Only called AFTER OTP is verified OR after user clicks Proceed on the Allow popup. This is where:
- The balance is deducted
- A transaction receipt is generated
- The transaction is added to the history list

**`validateForm()` (line 257):**
Checks before doing anything: is recipient filled? Does it have `@`? Is amount > 0? Is amount ≤ balance? Shows red error text if not.

---

### `mock-bank/styles.css` — All Visual Styling

**What it is:** Pure CSS that makes the bank look premium. Defines dark backgrounds, gradient cards, animations, and modal styles.

No logic here — purely visual. If something looks wrong, this is where you fix colors, sizes, animations.

---

## 🔌 LAYER 2 — The Chrome Extension (`extension/`)

The extension is a mini-program that lives inside Chrome and injects itself into web pages.

---

### `extension/manifest.json` — The Extension's ID Card

**What it is:** A config file Chrome reads to understand what permissions the extension needs and which scripts to load.

**Key settings:**

```json
"content_scripts": [{
  "matches": ["http://127.0.0.1:*/*", "http://localhost:*/*"],
  "js":  ["content.js"],
  "css": ["modal.css"]
}]
```
This says: "On any localhost page, inject content.js and modal.css automatically."

```json
"background": { "service_worker": "background.js" }
```
background.js runs silently in the background at all times.

```json
"host_permissions": ["http://127.0.0.1:8000/*"]
```
Grants permission to make network requests to the backend server.

---

### `extension/content.js` — The Interceptor (Most Critical Extension File)

**What it is:** Injected into the bank page. It "hijacks" the Pay button before the page's own code can react.

**How it attaches (line 50):**
```javascript
function attach() {
  const payButton = document.querySelector('#pay-btn');
  payButton.addEventListener('click', onButtonClick, true); // 'true' = capture phase
}
```
The `true` (capture phase) is crucial. Events in browsers travel DOWN the DOM tree before going back up. By listening in the capture phase, the extension's code fires BEFORE any other click handler — even the form's submit.

**`onButtonClick()` (line 144) — the main function:**
1. `e.preventDefault()` — stops the form from submitting
2. `e.stopImmediatePropagation()` — stops ALL other click handlers from running
3. Sets `window._fraudIntercepting = true` — signals to `script.js` to do nothing
4. Reads the amount and recipient from the form fields
5. Calls `callBackendWithRetry()` to ask the backend "is this fraud?"
6. Gets back `{ risk_score, action, reasons }`
7. If `window.fraudInterceptorReady` is true (script.js is loaded): fires the `fraudResult` custom event → script.js takes over the UI
8. If not: calls `showFallbackModal()` — shows its own basic popup

**`callBackend()` (line 187):**
```javascript
fetch('http://127.0.0.1:8000/risk', {
  method: 'POST',
  body: JSON.stringify({ user_id, amount, recipient, timestamp })
})
```
This is a standard HTTP POST request to the Python backend. It sends the transaction details and waits for the risk assessment.

**`callBackendWithRetry()` (line 207):**
Wraps `callBackend()` with 1 retry — if the first request fails, it waits 600ms and tries once more.

**`showFallbackModal()` (line 231):**
Creates a simple popup from scratch using JavaScript (no HTML needed). Used only when the bank page doesn't have `script.js`. Styled by `modal.css`.

**`setButtonState()` (line 219):**
Changes the Pay button to show "Checking security..." and a spinner while waiting for the backend.

---

### `extension/background.js` — The Silent Watcher

**What it is:** A service worker that runs in the background. Currently minimal.

```javascript
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete') activeTabs.add(tabId);
});
```
Tracks which tabs are loaded. Listens for messages from content.js. In this project it mostly just logs results and responds to PING messages.

---

### `extension/popup.html` + `extension/popup.js` — The Extension's Status Panel

**What it is:** The small panel you see when you click the extension icon in the Chrome toolbar.

**popup.html:** Defines the visual layout — shows status dots, threshold values, and whether the backend is online.

**popup.js:** 
- `checkBackend()`: Makes a GET request to `http://127.0.0.1:8000/health` — if the server responds, shows "✅ Online", otherwise "❌ Offline"
- `checkPageStatus()`: Runs a script in the current tab to check if `window.fraudInterceptorReady` is true (i.e., is the bank page loaded?)

---

### `extension/modal.css` — Fallback Modal Styling

Styles for the simple popup that `showFallbackModal()` creates. Only used on non-bank pages. Has `.fi-allow`, `.fi-verify`, `.fi-block` classes for color-coding.

---

## ⚙️ LAYER 3 — The Backend Server (`backend/`)

This is a Python **FastAPI** server. FastAPI is a framework for building APIs — programs that receive requests over the internet and send back responses.

You run it with: `uvicorn backend.main:app --reload`

---

### `backend/main.py` — The Server's Entry Point

**What it is:** The file that starts everything. When you run uvicorn, this is the file it reads.

```python
app = FastAPI(title="Fraud Interceptor API")
```
Creates the web server.

```python
app.mount("/bank", StaticFiles(directory="mock-bank", html=True))
```
Makes the mock bank website accessible at `http://127.0.0.1:8000/bank`. This is how you can open the bank in a browser through the Python server.

```python
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```
CORS = Cross-Origin Resource Sharing. Without this, the browser would block the extension from making requests to the Python server (security policy). `allow_origins=["*"]` allows anyone to call this API.

```python
app.include_router(risk_router)
```
Registers the `/risk` endpoint from `routes/risk.py`.

```python
@app.get("/health")
def health():
    return {"status": "ok", "block_threshold": 0.75, ...}
```
A simple endpoint the extension's popup uses to check if the server is running.

---

### `backend/config.py` — The Master Settings File

**What it is:** A single place for all important numbers. Never hardcode these in other files.

```python
BLOCK_THRESHOLD  = 0.75   # risk_score >= 0.75 → BLOCK
VERIFY_THRESHOLD = 0.55   # risk_score >= 0.55 → VERIFY (else ALLOW)
RULE_WEIGHT = 0.6         # Rule engine counts for 60% of final score
DL_WEIGHT   = 0.4         # AI model counts for 40% of final score
MAX_HISTORY = 5           # Remember last 5 transactions per user
SEQUENCE_LENGTH = 5       # Feed 5 past transactions to the LSTM
```

**To change how aggressive the blocking is, edit ONLY this file.**

---

### `backend/routes/risk.py` — The API Endpoint

**What it is:** Defines the `/risk` URL that the extension POSTs to.

**`TransactionRequest` class (line 46):**
```python
class TransactionRequest(BaseModel):
    user_id : str
    amount  : float
    recipient: str
    timestamp: Optional[float]
```
This is Pydantic model — it automatically validates incoming JSON. If `amount` is not a number, it rejects the request with a clear error message.

**The `@field_validator` functions:**
- `clean_user_id`: Strips whitespace, defaults to "anonymous" if blank
- `clean_recipient`: Strips whitespace
- `default_timestamp`: If no timestamp sent, uses current server time
- `coerce_amount`: Converts string "500" to float 500.0

**`RiskResponse` class (line 84):**
```python
class RiskResponse(BaseModel):
    risk_score : float    # 0.0 to 1.0
    action     : str      # "ALLOW", "VERIFY", or "BLOCK"
    reasons    : list     # List of human-readable strings
```

**`evaluate_risk()` endpoint (line 91):**
```python
@router.post("/risk", response_model=RiskResponse)
def evaluate_risk(payload: TransactionRequest):
    result = assess(payload.model_dump())  # Call the risk engine
    return RiskResponse(...)
```
Converts the incoming JSON → Python dict → passes to `assess()` → wraps response in `RiskResponse`.

**Note:** The old commented-out code at the top is previous versions. Only lines 29–114 (the uncommented part) actually run.

---

### `backend/services/risk_engine.py` — The Core Brain

**What it is:** The main logic coordinator. It takes a transaction, runs it through rules AND AI, combines the scores, and decides BLOCK/VERIFY/ALLOW.

**`_sanitise()` function (line 194):**
Cleans the transaction data and adds missing fields:
- Extracts the hour from the timestamp (e.g., 2 AM = suspicious)
- Calculates `amount_zscore` — how different is this amount from the user's average? (Z-score formula: `(current - average) / average`)
- Sets default values for all 8 features the LSTM needs

**`assess()` function (line 235) — the main function:**

**Step 1 — Nuclear Override: BLOCK**
```python
if amount >= 150000:
    return {"risk_score": 1.0, "action": "BLOCK", ...}
```
If amount ≥ ₹1,50,000 → instantly BLOCK. No AI needed.

**Step 2 — Nuclear Override: ALLOW**
```python
if amount < 500:
    return {"risk_score": 0.05, "action": "ALLOW", ...}
```
If amount < ₹500 → instantly ALLOW. Too small to worry about.

**Step 3 — Normal Pipeline (₹500 to ₹1,49,999):**
1. Call `rule_engine.evaluate(tx, history)` → get `rule_score` (0.0–1.0) and `flags`
2. Call `sequence_builder.build_sequence()` → prepare data for AI
3. Call `lstm_service.predict(sequence)` → get `dl_score` (0.0–1.0)
4. Combine: `final_score = (0.6 × rule_score) + (0.4 × dl_score)`
5. Save transaction to history (JSON file)
6. Return result based on thresholds

**Decision logic (line 282):**
```python
"action": "BLOCK" if final_score >= 0.75 else "VERIFY" if final_score >= 0.55 else "ALLOW"
```

---

### `backend/services/rule_engine.py` — The Rule-Based Checker

**What it is:** A simple set of hand-written "if this, then suspicious" rules.

**Current live code (line 84–94):**
```python
def evaluate(transaction, history):
    amount = transaction.get("amount", 0)
    rule_score = 0.0
    flags = []

    if amount >= 100000:           # ₹1 lakh or more
        rule_score = 1.0
        flags.append("SUSPICIOUS_HIGH_VALUE")
    
    return {"rule_score": rule_score, "flags": flags}
```

**Currently:** Only one rule — amounts ≥ ₹1,00,000 get `rule_score = 1.0`.

**Note:** All the commented-out code above are earlier versions with more rules (NEW_RECIPIENT, HIGH_VELOCITY etc.). They were disabled during development.

**The `flags` list** is what becomes the "reasons" shown to the user in the block/verify modal.

---

### `backend/services/lstm_service.py` — The AI Model

**What it is:** Loads a pre-trained LSTM (Long Short-Term Memory) neural network and uses it to score transactions.

**What is LSTM?** A type of AI that's good at understanding sequences — it looks at your last 5 transactions in order and asks "does the 6th one fit the pattern?"

**Startup (lines 55–69):**
```python
_MODEL = keras.models.load_model('backend/models/lstm_model.h5')
```
The model is loaded ONCE when the server starts. `_MODEL` is a global variable. If loading fails, `_MODEL = None`.

**`predict()` function (line 71):**
```python
def predict(sequence):
    if _MODEL is None:
        return {"dl_score": 0.5}  # Fallback: neutral score
    
    input_data = np.array(sequence).reshape(1, 5, 8)  # Shape: (1 batch, 5 timesteps, 8 features)
    prediction = _MODEL.predict(input_data, verbose=0)
    return {"dl_score": float(prediction[0][0])}
```
- Takes a `(5, 8)` array (5 transactions × 8 features each)
- Reshapes to `(1, 5, 8)` because the model expects a batch dimension
- Returns a score between 0.0 (normal) and 1.0 (very suspicious)

**If model fails:** Returns `{"dl_score": 0.5}` — a neutral score that won't cause false blocks.

---

### `backend/services/sequence_builder.py` — Preparing Data for the AI

**What it is:** Converts raw transaction history into the exact format the LSTM expects.

**`extract_features()` (line 50):**
```python
return [
    float(tx.get("amount", 0.0)),           # Feature 1: Amount
    float(tx.get("hour", 0.0)),              # Feature 2: Hour of day
    float(tx.get("amount_zscore", 0.0)),     # Feature 3: How unusual is the amount?
    float(tx.get("tx_frequency_60m", 0.0)), # Feature 4: How many txns in last 60 min?
    float(tx.get("device_fingerprint", 1.0)),# Feature 5: Device ID
    float(tx.get("location_consistency", 1.0)),# Feature 6: Usual location?
    float(tx.get("category_risk", 0.1)),    # Feature 7: Category risk level
    float(tx.get("account_age_days", 365))  # Feature 8: How old is the account?
]
```

**`build_sequence()` flow:**
1. Extract features from each past transaction
2. Add current transaction's features at the end
3. If history < 5 transactions: pad with zeros at the start
4. If history > 5: keep only the most recent 5
5. Load `scaler.pkl` (a StandardScaler that normalizes values)
6. Flatten to 1×40, apply scaler, reshape back to 5×8
7. Return as Python list

**Why scaling?** The LSTM was trained on normalized data. If you feed it raw amounts like ₹50,000, it won't work correctly — you need to transform the numbers to the same scale it was trained on.

---

### `backend/services/explanation.py` — Making Errors Human-Readable

**What it is:** Translates technical flag codes into plain English sentences.

```python
_FLAG_MESSAGES = {
    "AMOUNT_DEVIATION": "Transaction amount is significantly higher than your usual spending.",
    "NEW_RECIPIENT":    "Money is being sent to a recipient you have never transacted with before.",
    "HIGH_VELOCITY":    "Multiple transactions detected in a very short time window.",
    ...
}
```

**`build_reasons()` function:**
- For each flag from the rule engine, looks up the English message
- If `dl_score >= 0.75`: adds "AI model detected a strong anomaly..."
- If action is "ALLOW": returns empty list (no reasons needed)
- If action is "BLOCK": adds "Transaction has been BLOCKED for your protection."

**Note:** This file is NOT currently called by `risk_engine.py`. In the active code, `reasons` is just set to `rule_res.get("flags", [])` which returns the raw flag codes, not the English sentences. This is a known gap in the codebase.

---

### `backend/db/database.py` — Saving Transaction History

**What it is:** Reads and writes to `transaction_history.json` to remember past transactions.

**Why save history?** The LSTM needs to know your past 5 transactions to judge if the new one is suspicious.

**`_load_data()` (line 38):**
Opens `transaction_history.json` and parses it as a Python dictionary. Returns `{}` if file doesn't exist.

**`_save_data()` (line 48):**
Writes the entire dictionary back to the JSON file with nice formatting.

**`get_history(user_id)` (line 53):**
```python
db = _load_data()
return db.get(user_id, [])
```
Returns the list of past transactions for this user (or empty list if new user).

**`append_transaction(user_id, transaction)` (line 59):**
```python
db[user_id].append(transaction)
if len(db[user_id]) > 5:
    db[user_id] = db[user_id][-5:]  # Keep only last 5
_save_data(db)
```
Adds the new transaction. If user now has more than 5, deletes the oldest ones.

---

### `backend/db/schemas.py` — Just Documentation

**What it is:** A reference file that describes the shape of transaction dictionaries. Nothing imports this — it's just for developers to read.

---

## 🤖 LAYER 4 — Machine Learning (`ml/`)

### `ml/train.py` — Currently Empty

The training script is empty — the model was likely trained externally and the `.h5` file was added directly.

### `ml/model/scaler.pkl` — The Data Normalizer

A saved scikit-learn `StandardScaler`. Used by `sequence_builder.py` to normalize transaction features before feeding to the LSTM.

### `backend/models/lstm_model.h5` — The AI Brain File

The pre-trained Keras LSTM model saved in HDF5 format. `lstm_service.py` loads this file at startup. This is the actual neural network weights — the product of training on fraud data.

---

## 🔄 END-TO-END FLOW (What Actually Happens When You Click "Pay Now")

Here is the complete journey:

```
USER fills form → clicks "Pay Now"
         │
         ▼
extension/content.js intercepts click (capture phase)
  - Prevents form submit
  - Reads #amount and #recipient from the page
  - Sets window._fraudIntercepting = true
  - Shows "Checking security..." on button
         │
         ▼
content.js calls: POST http://127.0.0.1:8000/risk
  Body: { user_id, amount, recipient, timestamp }
         │
         ▼
backend/routes/risk.py receives request
  - Validates with Pydantic (TransactionRequest)
  - Calls assess(payload.model_dump())
         │
         ▼
backend/services/risk_engine.py → assess()
  - _sanitise(): cleans data, adds hour, zscore, etc.
  - Checks nuclear overrides (≥150k → BLOCK, <500 → ALLOW)
  - For mid-range amounts:
    │
    ├─→ rule_engine.evaluate(tx, history)
    │     - Returns rule_score + flags
    │
    ├─→ sequence_builder.build_sequence(tx, history)
    │     - Builds (5, 8) array of features
    │     - Scales using scaler.pkl
    │
    └─→ lstm_service.predict(sequence)
          - Loads lstm_model.h5 (already in memory)
          - Returns dl_score
         │
         ▼
  final_score = (0.6 × rule_score) + (0.4 × dl_score)
  action = BLOCK if ≥0.75, VERIFY if ≥0.55, else ALLOW
  append_transaction() → saves to transaction_history.json
  Returns { risk_score, action, reasons }
         │
         ▼
backend/routes/risk.py sends JSON response back to extension
         │
         ▼
content.js receives { risk_score, action, reasons }
  - Fires: document.dispatchEvent(new CustomEvent('fraudResult', { detail: riskData }))
         │
         ▼
mock-bank/script.js listener (line 747) receives 'fraudResult' event
  - Reads amount + recipient from form fields
  - Calls routeResponse(data, amount, recipient)
         │
    ┌────┴────┬──────────┐
    ▼         ▼          ▼
  ALLOW    VERIFY      BLOCK
    │         │          │
    ▼         ▼          ▼
show         Generate  Show red
green        OTP,      popup,
popup,       show OTP  log to
user clicks  popup,    history
"Proceed"    user      as blocked
    │        types OTP
    │             │
    ▼             ▼
completeTransaction()
  - Deducts balance
  - Shows receipt
  - Adds to history
```

---

## 🐛 Debugging Tips for Beginners

### "Backend not responding"
- Check if uvicorn is running: open `http://127.0.0.1:8000/health` in browser
- You should see `{"status": "ok", ...}`
- If not: run `uvicorn backend.main:app --reload` from the project root

### "Extension not working"
- Open Chrome → `chrome://extensions` → Enable "Developer mode" → Load Unpacked → select the `extension/` folder
- Check the extension popup — does it show "✅ Online"?
- Open DevTools on the bank page → Console tab → look for `[FraudInterceptor]` logs

### "Always getting ALLOW even for big amounts"
- Check `backend/config.py` → are thresholds set correctly?
- Check `backend/services/rule_engine.py` → is the evaluate() function returning a high rule_score?
- Add `print()` statements in `risk_engine.py`'s `assess()` to see what scores are being calculated

### "LSTM model not loading"
- Check the console when starting uvicorn — look for "✅ LSTM Model loaded" or "❌ Load Error"
- If error: the model file path may be wrong. Check `lstm_service.py` line 51

### "transaction_history.json has wrong data"
- Simply delete the file. The backend will create a fresh one automatically.

### "Modal not showing"
- Open browser DevTools → Console → look for JavaScript errors
- Check that `script.js` is loaded: in Console type `window.fraudInterceptorReady` — should print `true`

---

## 📋 Quick Reference: Which File to Edit for What

| I want to... | Edit this file |
|---|---|
| Change block/verify thresholds | `backend/config.py` |
| Add new fraud rules | `backend/services/rule_engine.py` |
| Change how the OTP popup looks | `mock-bank/styles.css` + `mock-bank/index.html` |
| Change OTP logic | `mock-bank/script.js` → `handleVerify()` |
| Change what the extension sends to backend | `extension/content.js` → `callBackend()` |
| Change API validation | `backend/routes/risk.py` → `TransactionRequest` |
| Add more human-readable reasons | `backend/services/explanation.py` |
| Fix "reasons not showing in English" | Wire `build_reasons()` into `risk_engine.py`'s `assess()` |
| Change how history is stored | `backend/db/database.py` |
| Retrain the AI model | `ml/train.py` (currently empty) |
