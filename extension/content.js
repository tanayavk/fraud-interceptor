/**
 * Fraud Interceptor — Content Script v3
 * ========================================
 * Injected into every page matching the manifest's content_scripts.
 *
 * Strategy:
 *   1. Attach a CAPTURE-phase click listener directly to #pay-btn.
 *      This fires before ANY other handler (including the form's own
 *      submit listener) and kills the native event lifecycle immediately.
 *   2. Scrape form values, call the fraud backend.
 *   3a. If window.fraudInterceptorReady is set (mock-bank page):
 *       dispatch 'fraudResult' — script.js owns the UI from here.
 *   3b. Otherwise: render our own fallback overlay modal.
 *   4. Overlay buttons are wired with addEventListener, NOT inline
 *      onclick attributes, avoiding scope issues.
 *   5. "Proceed Anyway" / "Proceed" uses HTMLFormElement.prototype.submit
 *      to bypass the content-script trap and trigger a native submission.
 */

'use strict';

/* ── Configuration ───────────────────────────────────────────────────── */
const CONFIG = {
  BACKEND_URL : 'http://127.0.0.1:8000/risk',
  USER_ID     : 'demo_user',
  TIMEOUT_MS  : 8000,
};

const SELECTORS = {
  FORM      : '#pay-form',
  PAY_BTN   : '#pay-btn',
  AMOUNT    : '#amount',
  RECIPIENT : '#recipient',
};

/* ── Guard flag — prevents re-entrancy ──────────────────────────────── */
let intercepting = false;

/* ════════════════════════════════════════════════════════════════════════
   ATTACH — wait for the DOM then hook the pay button
   ════════════════════════════════════════════════════════════════════════ */
let _attachAttempts = 0;

function attach() {
  _attachAttempts++;
  if (_attachAttempts > 40) {
    console.warn('[FraudInterceptor] #pay-btn not found after 20 s — giving up.');
    return;
  }

  const payButton = document.querySelector(SELECTORS.PAY_BTN);
  const form      = document.querySelector(SELECTORS.FORM);

  if (!payButton || !form) {
    setTimeout(attach, 500);
    return;
  }

  // Remove stale listener before re-adding (idempotent on hot-reload)
  payButton.removeEventListener('click', onButtonClick, true);
  // CAPTURE phase: we run before any bubble-phase handlers on the page
  payButton.addEventListener('click', onButtonClick, true);

  console.log('[FraudInterceptor] Attached capture listener to #pay-btn');
}

/* ════════════════════════════════════════════════════════════════════════
   BUTTON CLICK HANDLER (capture phase)
   ════════════════════════════════════════════════════════════════════════ */
async function onButtonClick(e) {
  // ── A. Kill the native event completely ──────────────────────────────
  e.preventDefault();
  e.stopPropagation();
  e.stopImmediatePropagation();

  // Reentrancy guard
  if (intercepting) return;
  intercepting = true;

  // Signal to script.js's own submit handler that we are in control
  window._fraudIntercepting = true;

  // ── B. Scrape form values ────────────────────────────────────────────
  const rawAmount = document.querySelector(SELECTORS.AMOUNT)?.value
                 ?? document.querySelector(SELECTORS.AMOUNT)?.innerText
                 ?? '';
  const amount    = parseFloat(String(rawAmount).replace(/,/g, ''));
  const recipient = (document.querySelector(SELECTORS.RECIPIENT)?.value || '').trim();

  // Basic validation — let the page's own error display handle it
  if (!recipient || isNaN(amount) || amount <= 0) {
    intercepting = false;
    window._fraudIntercepting = false;
    // Re-fire submit in the bubble phase so script.js validateForm() runs
    const form = document.querySelector(SELECTORS.FORM);
    if (form) {
      form.removeEventListener('submit', _noopCapture, true);
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    }
    return;
  }

  // ── C. Show loading state ────────────────────────────────────────────
  setButtonState(true);

  // ── D. Call the backend ──────────────────────────────────────────────
  let riskData;
  try {
    riskData = await callBackendWithRetry(amount, recipient);
  } catch (err) {
    console.warn('[FraudInterceptor] Backend unreachable — defaulting to VERIFY:', err);
    riskData = {
      risk_score : 0.5,
      action     : 'VERIFY',
      reasons    : ['Security service unreachable. Please verify manually.'],
    };
  }

  setButtonState(false);

  // ── E. Route to UI ───────────────────────────────────────────────────
  if (window.fraudInterceptorReady) {
    // Hand off to script.js — it owns the pretty OTP/block/allow modals
    document.dispatchEvent(new CustomEvent('fraudResult', {
      detail  : riskData,
      bubbles : false,
    }));
  } else {
    // No bank script — render our own overlay
    showFallbackModal(riskData, amount, recipient);
  }

  // ── F. Release guards ────────────────────────────────────────────────
  window._fraudIntercepting = false;
  intercepting = false;
}

// Noop used internally — keeps reference stable for removeEventListener
function _noopCapture() {}

/* ════════════════════════════════════════════════════════════════════════
   BACKEND CALLS
   ════════════════════════════════════════════════════════════════════════ */
async function callBackend(amount, recipient) {
  const controller = new AbortController();
  const timer      = setTimeout(() => controller.abort(), CONFIG.TIMEOUT_MS);

  try {
    const res = await fetch(CONFIG.BACKEND_URL, {
      method  : 'POST',
      headers : { 'Content-Type': 'application/json' },
      body    : JSON.stringify({
        user_id   : CONFIG.USER_ID,
        amount    : parseFloat(amount),
        recipient : recipient,
        timestamp : Date.now() / 1000,
      }),
      signal  : controller.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } finally {
    clearTimeout(timer);
  }
}

async function callBackendWithRetry(amount, recipient, retries = 1) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await callBackend(amount, recipient);
    } catch (err) {
      if (attempt === retries) throw err;
      await new Promise(r => setTimeout(r, 600));
    }
  }
}

/* ════════════════════════════════════════════════════════════════════════
   BUTTON LOADING STATE
   ════════════════════════════════════════════════════════════════════════ */
function setButtonState(loading) {
  const btn = document.querySelector(SELECTORS.PAY_BTN);
  if (!btn) return;

  btn.disabled = loading;

  const label   = btn.querySelector('#btn-text')   || btn.querySelector('.btn-label');
  const spinner = btn.querySelector('#btn-spinner') || btn.querySelector('.btn-loader');

  if (label)   label.textContent        = loading ? 'Checking security…' : 'Pay Now';
  if (spinner) spinner.style.display    = loading ? 'block' : 'none';

  btn.classList.toggle('loading', loading);
}

/* ════════════════════════════════════════════════════════════════════════
   FALLBACK MODAL  (for pages without script.js)
   ════════════════════════════════════════════════════════════════════════ */
function showFallbackModal(data, amount, recipient) {
  const pct    = Math.round((data.risk_score || 0) * 100);
  const action = (data.action || 'VERIFY').toUpperCase();
  const reasons = Array.isArray(data.reasons) ? data.reasons : [];

  // Per-action presentation config
  const cfg = {
    ALLOW: {
      icon  : '✅',
      cls   : 'fi-allow',
      title : 'Transaction Approved',
    },
    VERIFY: {
      icon  : '⚠️',
      cls   : 'fi-verify',
      title : 'Verification Recommended',
    },
    BLOCK: {
      icon  : '🚫',
      cls   : 'fi-block',
      title : 'Transaction Blocked',
    },
  };
  const c = cfg[action] || cfg.VERIFY;

  // Remove any previous overlay
  const existing = document.getElementById('fi-overlay');
  if (existing) existing.remove();

  // ── Build overlay element ────────────────────────────────────────────
  const overlay = document.createElement('div');
  overlay.id = 'fi-overlay';
  // Highest possible stacking context — sits above all page content
  overlay.style.cssText = [
    'position:fixed',
    'inset:0',
    'z-index:2147483647',
    'display:flex',
    'align-items:center',
    'justify-content:center',
    'background:rgba(0,0,0,0.65)',
    'backdrop-filter:blur(4px)',
  ].join(';') + ' !important';

  // ── Button rows — defined by action, NO inline onclick ───────────────
  // IDs are stable so external tests / debuggers can find them.
  let footerHTML = '';
  if (action === 'ALLOW') {
    footerHTML = `<button id="fi-btn-proceed" class="fi-btn fi-btn-success">Proceed</button>`;
  } else if (action === 'VERIFY') {
    footerHTML = `
      <button id="fi-btn-cancel"  class="fi-btn fi-btn-ghost">Cancel</button>
      <button id="fi-btn-proceed" class="fi-btn fi-btn-warning">Proceed Anyway</button>`;
  } else {
    // BLOCK
    footerHTML = `<button id="fi-btn-block" class="fi-btn fi-btn-danger">Understood</button>`;
  }

  // Build reasons HTML safely (no innerHTML injection from server data)
  const reasonsHTML = reasons.length
    ? `<div class="fi-reasons-label">Flags</div>
       <ul class="fi-reasons">${reasons.map(r => `<li>${_escHtml(r)}</li>`).join('')}</ul>`
    : '';

  overlay.innerHTML = `
    <div id="fi-modal">
      <div id="fi-header" class="${c.cls}">
        <div id="fi-icon">${c.icon}</div>
        <div>
          <div id="fi-title">${c.title}</div>
          <div id="fi-subtitle">
            ₹${parseFloat(amount).toLocaleString('en-IN')} → ${_escHtml(recipient)}
          </div>
        </div>
      </div>
      <div id="fi-body" class="${c.cls}">
        <div class="fi-score-row">
          <div>
            <div class="fi-score-label">Risk Score</div>
            <div class="fi-bar-bg">
              <div class="fi-bar-fill" style="width:${pct}%"></div>
            </div>
          </div>
          <div class="fi-score-value">${pct}%</div>
        </div>
        ${reasonsHTML}
      </div>
      <div id="fi-footer">${footerHTML}</div>
    </div>`;

  document.body.appendChild(overlay);

  // ── Wire buttons with addEventListener (no inline handlers) ──────────

  /**
   * closeAndProceed — dismisses the overlay then pushes the transaction
   * through to the bank's success screen.
   *
   * If window.fraudInterceptorReady is present, script.js is loaded and
   * owns the UI.  We dispatch a synthetic 'fraudResult' event carrying a
   * forced ALLOW payload so routeResponse() → handleAllow() runs and
   * shows the Proceed modal instead of looping back into VERIFY/OTP.
   *
   * If there is no script.js, we native-submit the form to move the page.
   */
  const closeAndProceed = () => {
    overlay.remove();

    if (window.fraudInterceptorReady) {
      // Force the bank UI into the ALLOW/success path regardless of the
      // original risk action (user has already accepted the risk).
      const allowPayload = {
        risk_score : data.risk_score,
        action     : 'ALLOW',   // ← key fix: do NOT re-send VERIFY
        reasons    : data.reasons,
      };
      document.dispatchEvent(new CustomEvent('fraudResult', {
        detail  : allowPayload,
        bubbles : false,
      }));
    } else {
      // No bank script — directly native-submit the form, bypassing
      // our capture listener via the HTMLFormElement prototype call.
      const form = document.querySelector(SELECTORS.FORM);
      if (form) HTMLFormElement.prototype.submit.call(form);
    }
  };

  const closeAndCancel = () => overlay.remove();

  const proceedBtn = overlay.querySelector('#fi-btn-proceed');
  const cancelBtn  = overlay.querySelector('#fi-btn-cancel');
  const blockBtn   = overlay.querySelector('#fi-btn-block');

  if (proceedBtn) proceedBtn.addEventListener('click', closeAndProceed);
  if (cancelBtn)  cancelBtn.addEventListener('click',  closeAndCancel);
  if (blockBtn)   blockBtn.addEventListener('click',   closeAndCancel);

  // Overlay MUST NOT be dismissed by clicking outside or pressing Escape.
  // No document-level escape / outside-click handlers attached here.
}

/* ── Simple HTML escaper to prevent XSS from server-returned strings ── */
function _escHtml(str) {
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}

/* ════════════════════════════════════════════════════════════════════════
   INIT
   ════════════════════════════════════════════════════════════════════════ */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', attach);
} else {
  attach();
}