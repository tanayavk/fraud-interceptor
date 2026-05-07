/**
 * SecureBank — Main Script
 * ===========================
 * Handles all banking UI interactions:
 *   - Login simulation
 *   - Tab navigation
 *   - Transaction form
 *   - Fraud response routing (ALLOW / VERIFY / BLOCK)
 *   - OTP generation, display, validation
 *   - Success receipt generation
 *   - Transaction history
 *
 * Extension integration:
 *   The extension intercepts the form submit, calls the backend,
 *   then fires: document.dispatchEvent(new CustomEvent('fraudResult', { detail: data }))
 *   This script listens for that event instead of calling the backend itself.
 *   If no extension is loaded, this script calls the backend as fallback.
 */

'use strict';

/* ════════════════════════════════════════════════════════════════
   CONFIG
   ════════════════════════════════════════════════════════════════ */
const BACKEND_URL = 'http://127.0.0.1:8000/risk';
const USER_ID     = 'demo_user';
const PHONE_MASK  = '+91 XXXXX89012';   // simulated phone for OTP display

/* ════════════════════════════════════════════════════════════════
   STATE
   ════════════════════════════════════════════════════════════════ */
let balance         = 8964570;
let monthlyDebit    = 14299;
let currentOTP      = null;
let otpTimer        = null;
let otpSecondsLeft  = 120;
let pendingTxn      = null;   // { amount, recipient, riskData }
let extensionPresent = false; // set to true if extension fires fraudResult

// Pre-populated transaction history
const txnHistory = [
  { id: 'TXN8821AA',  icon: '👤', name: 'Rahul Sharma',     upi: 'rahul.sharma@okaxis', amount: -1500,  time: 'Today, 10:24 AM',    status: 'success' },
  { id: 'TXN7734BB',  icon: '🛒', name: 'Amazon Pay',        upi: 'amazon@apl',          amount: -3299,  time: 'Yesterday, 3:15 PM',  status: 'success' },
  { id: 'TXN6612CC',  icon: '❓', name: 'Unknown Merchant',  upi: 'suspicious@xpay',     amount: -25000, time: '2 days ago, 2:47 AM', status: 'blocked' },
  { id: 'TXN5500DD',  icon: '💰', name: 'Salary Credit',     upi: 'employer@hdfcbank',   amount: +65000, time: 'Apr 30, 9:00 AM',     status: 'success' },
  { id: 'TXN4490EE',  icon: '🏠', name: 'Priya Mehta',       upi: 'priyam@ybl',          amount: -8000,  time: 'Apr 28, 6:30 PM',    status: 'success' },
];

const CONTACTS = [
  { name: 'Rahul Sharma', upi: 'rahul.sharma@okaxis', icon: '👤' },
  { name: 'Priya Mehta',  upi: 'priyam@ybl',          icon: '👩' },
  { name: 'Amazon Pay',   upi: 'amazon@apl',           icon: '🛒' },
  { name: '⚠ Unknown',   upi: 'newmerchant99@paytm',  icon: '❓' },
];

/* ════════════════════════════════════════════════════════════════
   DOM HELPERS
   ════════════════════════════════════════════════════════════════ */
const $  = id  => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

function show(id)    { $(id).classList.remove('hidden'); }
function hide(id)    { $(id).classList.add('hidden'); }
function isHidden(id){ return $(id).classList.contains('hidden'); }

function setLoading(btnId, on) {
  const btn = $(btnId);
  if (!btn) return;
  btn.classList.toggle('loading', on);
  btn.disabled = on;
}

/* ════════════════════════════════════════════════════════════════
   LOGIN
   ════════════════════════════════════════════════════════════════ */
// $('login-form').addEventListener('submit', e => {
//   e.preventDefault();
//   setLoading('login-btn', true);
//   setTimeout(() => {
//     $('screen-login').classList.remove('active');
//     $('screen-dashboard').classList.add('active');
//     renderHistory();
//     renderContacts();
//     setLoading('login-btn', false);
//   }, 1200);
// });

// 1. Use getElementById (no # needed) or querySelector (needs #)
const loginForm = document.getElementById('login-form');
const logoutBtn = document.getElementById('logout-btn');

if (loginForm) {
    loginForm.addEventListener('submit', e => {
        e.preventDefault();
        showDashboard();
    });
}

function showDashboard() {
    const loginScreen = document.getElementById('screen-login');
    const dashboardScreen = document.getElementById('screen-dashboard');

    // Only try to remove the class if the login screen actually exists
    if (loginScreen) {
        loginScreen.classList.remove('active');
    }

    // Only try to add the class if the dashboard exists
    if (dashboardScreen) {
        dashboardScreen.classList.add('active');
    }

    // These should still run as long as they don't rely on the commented-out HTML
    renderHistory();
    renderContacts();
}

if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
        // Note: You used $('screen-dashboard') here too, changed to getElementById
        document.getElementById('screen-dashboard')?.classList.remove('active');
        document.getElementById('screen-login')?.classList.add('active');
    });
}

/* ════════════════════════════════════════════════════════════════
   NAVIGATION TABS
   ════════════════════════════════════════════════════════════════ */
$$('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const tab = link.dataset.tab;
    $$('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    $$('.tab-section').forEach(s => s.classList.remove('active'));
    $(`tab-${tab}`).classList.add('active');
    // Close mobile nav
    $('main-nav').classList.remove('open');
  });
});

$('hamburger').addEventListener('click', () => {
  $('main-nav').classList.toggle('open');
});

// History filter buttons
$$('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    $$('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderHistory(btn.dataset.filter);
  });
});

/* ════════════════════════════════════════════════════════════════
   QUICK AMOUNTS & CONTACTS
   ════════════════════════════════════════════════════════════════ */
$$('.qa-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    $('amount').value = chip.dataset.amt;
    $('amount').focus();
  });
});

function renderContacts() {
  const grid = $('contact-grid');
  grid.innerHTML = CONTACTS.map(c => `
    <div class="contact-item" data-upi="${c.upi}">
      <div class="contact-name">${c.name}</div>
      <div class="contact-upi">${c.upi}</div>
    </div>`).join('');

  grid.querySelectorAll('.contact-item').forEach(item => {
    item.addEventListener('click', () => {
      $('recipient').value = item.dataset.upi;
      $('amount').focus();
      // Switch to transfer tab if not active
      const transferLink = document.querySelector('[data-tab="transfer"]');
      if (transferLink) transferLink.click();
    });
  });
}

/* ════════════════════════════════════════════════════════════════
   TRANSACTION HISTORY
   ════════════════════════════════════════════════════════════════ */
function renderHistory(filter = 'all') {
  const list  = $('txn-list');
  const empty = $('txn-empty');
  const items = filter === 'all'
    ? txnHistory
    : txnHistory.filter(t => t.status === filter);

  if (items.length === 0) {
    list.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  list.innerHTML = items.map(t => {
    const sign    = t.amount > 0 ? '+' : '−';
    const absAmt  = Math.abs(t.amount).toLocaleString('en-IN');
    const cls     = t.amount > 0 ? 'credit' : 'debit';
    return `
    <li class="txn-item" data-status="${t.status}">
      <div class="txn-left">
        <div class="txn-icon">${t.icon}</div>
        <div>
          <div class="txn-name">${t.name}</div>
          <div class="txn-upi">${t.upi}</div>
        </div>
      </div>
      <div class="txn-right">
        <div class="txn-amount ${cls}">${sign} ₹${absAmt}</div>
        <div class="txn-time">${t.time}</div>
        <span class="txn-badge ${t.status}">${t.status.toUpperCase()}</span>
      </div>
    </li>`;
  }).join('');
}

function addToHistory(txn) {
  txnHistory.unshift(txn);
  renderHistory();
}

/* ════════════════════════════════════════════════════════════════
   BALANCE UPDATE
   ════════════════════════════════════════════════════════════════ */
function deductBalance(amount) {
  balance      -= amount;
  monthlyDebit += amount;

  $('balance-display').textContent =
    '₹ ' + balance.toLocaleString('en-IN', { minimumFractionDigits: 2 });
  $('acct-bal-savings').textContent =
    '₹ ' + balance.toLocaleString('en-IN', { minimumFractionDigits: 2 });
  $('month-debit').textContent =
    '− ₹' + monthlyDebit.toLocaleString('en-IN');
}

/* ════════════════════════════════════════════════════════════════
   STATUS BANNER
   ════════════════════════════════════════════════════════════════ */
function showBanner(type, message) {
  const b = $('status-banner');
  b.className = `status-banner ${type}`;
  b.innerHTML = message;
  b.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  if (type === 'success') setTimeout(() => b.classList.add('hidden'), 10000);
}

/* ════════════════════════════════════════════════════════════════
   FORM VALIDATION
   ════════════════════════════════════════════════════════════════ */
function validateForm() {
  let valid = true;
  const recipient = $('recipient').value.trim();
  const amount    = parseFloat($('amount').value);

  $('err-recipient').textContent = '';
  $('err-amount').textContent    = '';
  $('recipient').classList.remove('input-error');
  $('amount').classList.remove('input-error');

  if (!recipient) {
    $('err-recipient').textContent = 'Please enter a recipient UPI ID.';
    $('recipient').classList.add('input-error');
    valid = false;
  } else if (!recipient.includes('@')) {
    $('err-recipient').textContent = 'Enter a valid UPI ID (name@bank).';
    $('recipient').classList.add('input-error');
    valid = false;
  }
  if (!amount || amount <= 0) {
    $('err-amount').textContent = 'Enter an amount greater than ₹0.';
    $('amount').classList.add('input-error');
    valid = false;
  } else if (amount > 200000) {
    $('err-amount').textContent = 'Daily limit is ₹2,00,000.';
    $('amount').classList.add('input-error');
    valid = false;
  } else if (amount > balance) {
    $('err-amount').textContent = 'Insufficient balance.';
    $('amount').classList.add('input-error');
    valid = false;
  }
  return valid;
}

/* ════════════════════════════════════════════════════════════════
   MAIN PAY FLOW
   ════════════════════════════════════════════════════════════════ */
$('pay-form').addEventListener('submit', async e => {
  e.preventDefault();
  if (!validateForm()) return;

  const amount    = parseFloat($('amount').value);
  const recipient = $('recipient').value.trim();

  hide('status-banner');
  setLoading('pay-btn', true);

  // Extension fires 'fraudResult' event if present;
  // wait up to 6 seconds for it before falling back.
  let riskData = null;

  const extensionResult = await waitForExtension(amount, recipient);
  if (extensionResult) {
    riskData = extensionResult;
  } else {
    // No extension — call backend directly
    try {
      const res = await fetch(BACKEND_URL, {
        method : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body   : JSON.stringify({ user_id: USER_ID, amount, recipient }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      riskData = await res.json();
    } catch (err) {
      console.warn('[SecureBank] Backend unreachable — simulating VERIFY:', err);
      riskData = {
        risk_score : 0.5,
        action     : 'VERIFY',
        reasons    : ['Security check could not complete. Verification required.'],
      };
    }
  }

  setLoading('pay-btn', false);
  pendingTxn = { amount, recipient, riskData };
  routeResponse(riskData, amount, recipient);
});

/* Waits for the extension to fire a 'fraudResult' event.
   Returns the event detail, or null if no event within timeout. */
function waitForExtension(amount, recipient) {
  return new Promise(resolve => {
    let resolved = false;
    
    // Increase timeout to 10 seconds to allow the backend to respond
    const timeout = setTimeout(() => {
      if (!resolved) { 
          resolved = true; 
          console.log("[SecureBank] Extension timeout - falling back to direct call");
          resolve(null); 
      }
    }, 30000); 

    document.addEventListener('fraudResult', function handler(e) {
      document.removeEventListener('fraudResult', handler);
      clearTimeout(timeout);
      if (!resolved) { 
          resolved = true; 
          console.log("[SecureBank] Data received from extension");
          resolve(e.detail); 
      }
    }, { once: true });
  });
}

/* ════════════════════════════════════════════════════════════════
   RESPONSE ROUTER
   ════════════════════════════════════════════════════════════════ */
function routeResponse(data, amount, recipient) {
  const action = data.action;
  if      (action === 'ALLOW')  handleAllow(amount, recipient, data);
  else if (action === 'VERIFY') handleVerify(amount, recipient, data);
  else                          handleBlock(amount, recipient, data);
}

/* ════════════════════════════════════════════════════════════════
   ALLOW — silent pass-through
   ════════════════════════════════════════════════════════════════ */
function handleAllow(amount, recipient, data) {
  completeTransaction(amount, recipient, 'direct');
}

/* ════════════════════════════════════════════════════════════════
   VERIFY — OTP flow
   ════════════════════════════════════════════════════════════════ */
function handleVerify(amount, recipient, data) {
  // Generate 6-digit OTP
  currentOTP = String(Math.floor(100000 + Math.random() * 900000));

  // Populate transaction summary
  $('otp-txn-summary').innerHTML = `
    <div>
      <div class="sum-label">Sending To</div>
      <div class="sum-val">${recipient}</div>
    </div>
    <div>
      <div class="sum-label">Mode</div>
      <div class="sum-val">${$('txn-type').value}</div>
    </div>
    <div style="grid-column:span 2">
      <div class="sum-label">Amount</div>
      <div class="sum-val big">₹ ${amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
    </div>`;

  // Populate SMS preview
  $('sms-body').innerHTML = `
    SecureBank: OTP for ₹${amount.toLocaleString('en-IN')} transfer to ${recipient}
    is <span class="sms-otp">${currentOTP}</span>.
    Valid for 2 minutes. Do NOT share with anyone. -SECBNK`;
  $('sms-time').textContent = 'Just now';

  // Show risk info if reasons provided
  const reasons = data.reasons || [];
  $('risk-info').textContent = reasons.length
    ? '⚠ ' + reasons.filter(r => !r.includes('verify') && !r.includes('BLOCKED')).join(' · ')
    : '';

  // Reset OTP inputs
  clearOtpInputs();
  hide('otp-error');
  $('otp-error').textContent = 'Incorrect OTP. Please try again.';

  // Start countdown
  startOtpTimer();

  show('otp-overlay');
  // Focus first input after animation
  setTimeout(() => $$('.otp-box')[0]?.focus(), 300);
}

/* ════════════════════════════════════════════════════════════════
   BLOCK — show block modal
   ════════════════════════════════════════════════════════════════ */
function handleBlock(amount, recipient, data) {
  const pct = Math.round(data.risk_score * 100);

  $('block-txn-summary').innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <div style="font-size:11px;color:var(--muted)">Attempted Transfer</div>
        <div style="font-size:16px;font-weight:700;font-family:'DM Mono',monospace;color:var(--red);margin-top:3px">
          ₹ ${amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </div>
        <div style="font-size:12px;color:var(--text2);margin-top:2px">To: ${recipient}</div>
      </div>
      <div style="font-size:36px">🚫</div>
    </div>`;

  $('risk-meter').innerHTML = `
    <div class="risk-meter-label">Risk Score</div>
    <div class="risk-bar-bg">
      <div class="risk-bar-fill" id="risk-bar" style="width:0%"></div>
    </div>
    <div class="risk-score-val">${pct}% Risk</div>`;

  const reasons = (data.reasons || []).filter(r => r);
  $('block-reasons').innerHTML = reasons.length
    ? reasons.map(r => `<li>${r}</li>`).join('')
    : '<li>Automated fraud signals triggered.</li>';

  show('block-overlay');
  // Animate bar
  setTimeout(() => {
    const bar = $('risk-bar');
    if (bar) bar.style.width = pct + '%';
  }, 150);

  // Log to history
  addToHistory({
    id     : 'TXN' + Date.now().toString(36).toUpperCase().slice(-6),
    icon   : '🚫',
    name   : recipient,
    upi    : recipient,
    amount : -amount,
    time   : 'Just now',
    status : 'blocked',
  });

  showBanner('blocked', `🚫 <strong>Transaction Blocked</strong> — ₹${amount.toLocaleString('en-IN')} to ${recipient}. Risk score: ${pct}%.`);
  $('pay-form').reset();
}

/* ════════════════════════════════════════════════════════════════
   OTP LOGIC
   ════════════════════════════════════════════════════════════════ */
function startOtpTimer() {
  clearInterval(otpTimer);
  otpSecondsLeft = 120;
  show('otp-timer-text');
  hide('resend-btn');
  updateTimerDisplay();

  otpTimer = setInterval(() => {
    otpSecondsLeft--;
    if (otpSecondsLeft <= 0) {
      clearInterval(otpTimer);
      $('otp-timer-text').innerHTML = 'OTP expired.';
      show('resend-btn');
      hide('otp-timer-text');
      // Disable verify button
      $('otp-verify-btn').disabled = true;
    } else {
      updateTimerDisplay();
    }
  }, 1000);
}

function updateTimerDisplay() {
  const m = String(Math.floor(otpSecondsLeft / 60)).padStart(2, '0');
  const s = String(otpSecondsLeft % 60).padStart(2, '0');
  const countdown = $('otp-countdown');
  if (countdown) countdown.textContent = `${m}:${s}`;
}

function clearOtpInputs() {
  $$('.otp-box').forEach(box => {
    box.value = '';
    box.classList.remove('filled', 'error');
  });
  $('otp-verify-btn').disabled = false;
}

// OTP box keyboard handling — digit entry with auto-advance
$('otp-inputs').addEventListener('keydown', e => {
  const boxes = Array.from($$('.otp-box'));
  const idx   = parseInt(e.target.dataset.index);

  if (e.key === 'Backspace') {
    e.preventDefault();
    if (e.target.value) {
      e.target.value = '';
      e.target.classList.remove('filled');
    } else if (idx > 0) {
      boxes[idx - 1].focus();
    }
    return;
  }
  if (e.key === 'ArrowLeft'  && idx > 0)              { boxes[idx - 1].focus(); return; }
  if (e.key === 'ArrowRight' && idx < boxes.length-1) { boxes[idx + 1].focus(); return; }
  if (!/^\d$/.test(e.key)) { e.preventDefault(); return; }
});

$('otp-inputs').addEventListener('input', e => {
  const boxes = Array.from($$('.otp-box'));
  const idx   = parseInt(e.target.dataset.index);
  const val   = e.target.value;

  if (!/^\d$/.test(val)) { e.target.value = ''; return; }

  e.target.classList.add('filled');
  e.target.classList.remove('error');

  if (idx < boxes.length - 1) {
    boxes[idx + 1].focus();
  } else {
    // Last box filled — auto-verify
    $('otp-verify-btn').focus();
  }
});

// Paste support
$('otp-inputs').addEventListener('paste', e => {
  e.preventDefault();
  const pasted = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '').slice(0, 6);
  const boxes  = $$('.otp-box');
  pasted.split('').forEach((d, i) => {
    if (boxes[i]) {
      boxes[i].value = d;
      boxes[i].classList.add('filled');
    }
  });
  if (pasted.length === 6) $('otp-verify-btn').focus();
});

// Verify button
$('otp-verify-btn').addEventListener('click', () => {
  const entered = Array.from($$('.otp-box')).map(b => b.value).join('');
  if (entered.length < 6) {
    showOtpError('Please enter all 6 digits.');
    return;
  }
  if (entered !== currentOTP) {
    showOtpError('Incorrect OTP. Please try again.');
    $$('.otp-box').forEach(b => b.classList.add('error'));
    setTimeout(() => {
      $$('.otp-box').forEach(b => { b.classList.remove('error'); b.value = ''; b.classList.remove('filled'); });
      $$('.otp-box')[0]?.focus();
    }, 600);
    return;
  }

  // OTP correct
  setLoading('otp-verify-btn', true);
  clearInterval(otpTimer);

  setTimeout(() => {
    setLoading('otp-verify-btn', false);
    hide('otp-overlay');
    if (pendingTxn) {
      completeTransaction(pendingTxn.amount, pendingTxn.recipient, 'otp-verified');
    }
  }, 800);
});

function showOtpError(msg) {
  const el = $('otp-error');
  el.textContent = msg;
  el.classList.remove('hidden');
}

// Cancel OTP
$('otp-cancel-btn').addEventListener('click', () => {
  clearInterval(otpTimer);
  hide('otp-overlay');
  clearOtpInputs();
  showBanner('warning', '⚠ Transaction cancelled by you.');
  pendingTxn = null;
});

// Resend OTP
$('resend-btn').addEventListener('click', () => {
  currentOTP = String(Math.floor(100000 + Math.random() * 900000));
  $('sms-body').innerHTML = `
    SecureBank: New OTP for your transfer is
    <span class="sms-otp">${currentOTP}</span>.
    Valid for 2 minutes. Do NOT share. -SECBNK`;
  $('sms-time').textContent = 'Just now';
  $('otp-timer-text').innerHTML = 'Resend in <b id="otp-countdown">02:00</b>';
  show('otp-timer-text');
  hide('resend-btn');
  clearOtpInputs();
  hide('otp-error');
  $('otp-verify-btn').disabled = false;
  startOtpTimer();
  $$('.otp-box')[0]?.focus();
});

/* ════════════════════════════════════════════════════════════════
   BLOCK MODAL CLOSE
   ════════════════════════════════════════════════════════════════ */
$('block-ok-btn').addEventListener('click', () => {
  hide('block-overlay');
  pendingTxn = null;
});

/* ════════════════════════════════════════════════════════════════
   COMPLETE TRANSACTION → SUCCESS RECEIPT
   ════════════════════════════════════════════════════════════════ */
function completeTransaction(amount, recipient, method) {
  const txnId    = 'TXN' + Date.now().toString(36).toUpperCase().slice(-8);
  const now      = new Date();
  const timeStr  = now.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true
  });
  const methodLabel = method === 'otp-verified'
    ? `${$('txn-type')?.value || 'UPI'} (OTP Verified)`
    : $('txn-type')?.value || 'UPI';

  // Build receipt
  $('receipt').innerHTML = `
    <div class="receipt-row">
      <span class="r-label">Amount Sent</span>
      <span class="r-val amount">₹ ${amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
    </div>
    <div class="receipt-row">
      <span class="r-label">To</span>
      <span class="r-val">${recipient}</span>
    </div>
    <div class="receipt-row">
      <span class="r-label">Mode</span>
      <span class="r-val">${methodLabel}</span>
    </div>
    <div class="receipt-row">
      <span class="r-label">Date & Time</span>
      <span class="r-val">${timeStr}</span>
    </div>
    <div class="receipt-row">
      <span class="r-label">Transaction ID</span>
      <span class="r-val">${txnId}</span>
    </div>
    <div class="receipt-row">
      <span class="r-label">Status</span>
      <span class="r-val green">✓ Successful</span>
    </div>`;

  show('success-overlay');

  // Update balance
  deductBalance(amount);

  // Add to history
  addToHistory({
    id     : txnId,
    icon   : '✅',
    name   : recipient,
    upi    : recipient,
    amount : -amount,
    time   : 'Just now',
    status : 'success',
  });

  showBanner('success', `✅ <strong>₹${amount.toLocaleString('en-IN')} sent successfully</strong> to ${recipient}. ID: ${txnId}`);

  pendingTxn  = null;
  currentOTP  = null;
}

$('success-ok-btn').addEventListener('click', () => {
  hide('success-overlay');
  $('pay-form').reset();
  $('err-recipient').textContent = '';
  $('err-amount').textContent    = '';
});

/* ════════════════════════════════════════════════════════════════
   EXTENSION BRIDGE
   Exposes window.fraudInterceptorReady so extension can check
   that the page script is loaded before firing the event.
   ════════════════════════════════════════════════════════════════ */
window.fraudInterceptorReady = true;

/* The extension fires this event instead of calling backend itself.
   This makes extension and page cleanly decoupled. */
document.addEventListener('fraudResult', e => {
  extensionPresent = true;
  // The form submit handler catches this via waitForExtension()
  // — no extra handling needed here.
  console.log('[SecureBank] Received fraudResult from extension:', e.detail);
});

/* ════════════════════════════════════════════════════════════════
   KEYBOARD: Escape to close overlays
   ════════════════════════════════════════════════════════════════ */
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  if (!isHidden('otp-overlay'))  $('otp-cancel-btn').click();
  if (!isHidden('block-overlay'))$('block-ok-btn').click();
  if (!isHidden('success-overlay')) $('success-ok-btn').click();
});

/* ════════════════════════════════════════════════════════════════
   INIT
   ════════════════════════════════════════════════════════════════ */

// This runs automatically when the page loads
window.addEventListener('DOMContentLoaded', () => {
    showDashboard(); 
    console.log("Dashboard forced active for testing.");
});

renderHistory();
renderContacts();