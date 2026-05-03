/**
 * Fraud Interceptor — Content Script
 * =====================================
 * Injected into the banking page by Chrome.
 * Intercepts the #pay-btn click, contacts the backend,
 * and shows a styled risk modal before allowing payment.
 *
 * Works with mock-bank/index.html out of the box.
 * For real banking sites: change the selectors in SELECTORS below.
 */

'use strict';

// ── Configuration ────────────────────────────────────────────────────────
const CONFIG = {
  BACKEND_URL : 'http://127.0.0.1:8000/risk',
  USER_ID     : 'demo_user',          // change to session-based ID in prod
  TIMEOUT_MS  : 5000,                 // max wait for backend
};

// ── DOM Selectors — change these to match real banking sites ──────────────
const SELECTORS = {
  PAY_BUTTON : '#pay-btn',
  AMOUNT     : '#amount',
  RECIPIENT  : '#recipient',
  FORM       : '#pay-form',
};

// ── State ────────────────────────────────────────────────────────────────
let interceptActive = false;     // prevent double-click during processing
let pendingResolve  = null;      // resolves when user clicks modal button

// ════════════════════════════════════════════════════════════════════════
//  MAIN INTERCEPT
// ════════════════════════════════════════════════════════════════════════

function attachInterceptor() {
  const payBtn = document.querySelector(SELECTORS.PAY_BUTTON);
  if (!payBtn) {
    // Page not ready yet — retry
    setTimeout(attachInterceptor, 500);
    return;
  }

  // Override the form's default submit behaviour
  const form = document.querySelector(SELECTORS.FORM);
  if (form) {
    form.addEventListener('submit', onPayAttempt, true);  // capture phase
  }

  // Also cover direct button clicks
  payBtn.addEventListener('click', e => {
    if (interceptActive) { e.preventDefault(); e.stopPropagation(); }
  }, true);

  console.log('[FraudInterceptor] Attached to pay button.');
}

async function onPayAttempt(e) {
  e.preventDefault();
  e.stopImmediatePropagation();

  if (interceptActive) return;
  interceptActive = true;

  const amount    = getFieldValue(SELECTORS.AMOUNT);
  const recipient = getFieldValue(SELECTORS.RECIPIENT);

  // Basic local validation before hitting backend
  if (!recipient || !amount || parseFloat(amount) <= 0) {
    interceptActive = false;
    return;   // let the page's own validation handle this
  }

  // Set UI to loading
  setPayButtonLoading(true);

  // Call backend
  let riskData;
  try {
    riskData = await fetchRiskScore(amount, recipient);
  } catch (err) {
    console.warn('[FraudInterceptor] Backend unreachable, defaulting to VERIFY:', err);
    riskData = {
      risk_score : 0.5,
      action     : 'VERIFY',
      reasons    : ['Could not reach fraud detection server. Proceed with caution.'],
    };
  }

  setPayButtonLoading(false);

  // ── ALLOW: silent pass-through ──────────────────────────────────────
  if (riskData.action === 'ALLOW') {
    console.log('[FraudInterceptor] ALLOW — passing through.');
    interceptActive = false;
    // Call the page's handleFraudResponse if it exists, else just submit
    if (typeof window.handleFraudResponse === 'function') {
      window.handleFraudResponse(riskData, parseFloat(amount), recipient);
    }
    return;
  }

  // ── VERIFY or BLOCK: show modal ─────────────────────────────────────
  const userDecision = await showModal(riskData, amount, recipient);

  interceptActive = false;

  if (userDecision === 'proceed') {
    // User confirmed despite warning — let it through
    if (typeof window.handleFraudResponse === 'function') {
      window.handleFraudResponse(
        { risk_score: riskData.risk_score, action: 'ALLOW', reasons: [] },
        parseFloat(amount), recipient
      );
    }
  } else {
    // Blocked or user cancelled
    if (typeof window.handleFraudResponse === 'function') {
      window.handleFraudResponse(riskData, parseFloat(amount), recipient);
    }
  }
}

// ════════════════════════════════════════════════════════════════════════
//  BACKEND CALL
// ════════════════════════════════════════════════════════════════════════

async function fetchRiskScore(amount, recipient) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), CONFIG.TIMEOUT_MS);

  const response = await fetch(CONFIG.BACKEND_URL, {
    method  : 'POST',
    headers : { 'Content-Type': 'application/json' },
    body    : JSON.stringify({
      user_id   : CONFIG.USER_ID,
      amount    : parseFloat(amount),
      recipient : recipient,
    }),
    signal  : controller.signal,
  });

  clearTimeout(timer);

  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}`);
  }
  return response.json();
}

// ════════════════════════════════════════════════════════════════════════
//  MODAL
// ════════════════════════════════════════════════════════════════════════

function showModal(data, amount, recipient) {
  return new Promise(resolve => {
    pendingResolve = resolve;

    const action     = data.action;      // "VERIFY" or "BLOCK"
    const score      = data.risk_score;  // 0.0 – 1.0
    const reasons    = data.reasons || [];
    const pct        = Math.round(score * 100);

    // ── Config per action ─────────────────────────────────────────
    const cfg = {
      BLOCK: {
        icon      : '🚫',
        title     : 'Transaction Blocked',
        subtitle  : 'This transaction has been stopped for your security.',
        cls       : 'fi-block',
        scoreLabel: 'Risk Level: HIGH',
        buttons   : `
          <button class="fi-btn fi-btn-danger" onclick="fiClose('blocked')">Confirm Block</button>`,
      },
      VERIFY: {
        icon      : '⚠️',
        title     : 'Suspicious Transaction',
        subtitle  : 'Please review before proceeding.',
        cls       : 'fi-verify',
        scoreLabel: 'Risk Level: MEDIUM',
        buttons   : `
          <button class="fi-btn fi-btn-ghost"   onclick="fiClose('cancelled')">Cancel Payment</button>
          <button class="fi-btn fi-btn-warning"  onclick="fiClose('proceed')">Proceed Anyway</button>`,
      },
    };

    const c = cfg[action] || cfg.VERIFY;

    // ── Reason list HTML ──────────────────────────────────────────
    const reasonsHtml = reasons.length
      ? `<div class="fi-reasons-label">Why we flagged this</div>
         <ul class="fi-reasons">${reasons.map(r => `<li>${r}</li>`).join('')}</ul>`
      : `<p class="fi-no-reasons">Automated risk signals detected.</p>`;

    // ── Transaction summary ───────────────────────────────────────
    const summary = `
      <div class="fi-score-row">
        <div>
          <div class="fi-score-label">${c.scoreLabel}</div>
          <div style="font-size:12px;color:#c5d1e8;margin-top:4px;">
            ₹${parseFloat(amount).toLocaleString('en-IN')} → ${recipient}
          </div>
          <div class="fi-bar-bg"><div class="fi-bar-fill" style="width:${pct}%"></div></div>
        </div>
        <div class="fi-score-value">${pct}%</div>
      </div>`;

    // ── Build modal HTML ──────────────────────────────────────────
    const overlay = document.createElement('div');
    overlay.id = 'fi-overlay';
    overlay.innerHTML = `
      <div id="fi-modal">
        <div id="fi-header" class="${c.cls}">
          <div id="fi-icon">${c.icon}</div>
          <div>
            <div id="fi-title">${c.title}</div>
            <div id="fi-subtitle">${c.subtitle}</div>
          </div>
        </div>
        <div id="fi-body" class="${c.cls}">
          ${summary}
          ${reasonsHtml}
        </div>
        <div id="fi-footer">${c.buttons}</div>
      </div>`;

    document.body.appendChild(overlay);

    // Close on overlay click (only for VERIFY, not BLOCK)
    if (action === 'VERIFY') {
      overlay.addEventListener('click', e => {
        if (e.target === overlay) fiClose('cancelled');
      });
    }

    // Keyboard: Escape to cancel
    document.addEventListener('keydown', onEsc);
  });
}

function fiClose(decision) {
  const overlay = document.getElementById('fi-overlay');
  if (overlay) overlay.remove();
  document.removeEventListener('keydown', onEsc);
  if (pendingResolve) {
    pendingResolve(decision);
    pendingResolve = null;
  }
}

function onEsc(e) {
  if (e.key === 'Escape') fiClose('cancelled');
}

// Expose to inline onclick handlers in the injected HTML
window.fiClose = fiClose;

// ════════════════════════════════════════════════════════════════════════
//  UTILITIES
// ════════════════════════════════════════════════════════════════════════

function getFieldValue(selector) {
  const el = document.querySelector(selector);
  return el ? el.value.trim() : '';
}

function setPayButtonLoading(on) {
  const btn = document.querySelector(SELECTORS.PAY_BUTTON);
  if (!btn) return;
  btn.disabled = on;
  const textEl = btn.querySelector('#btn-text');
  const spinEl = btn.querySelector('#btn-spinner');
  if (textEl) textEl.textContent = on ? 'Checking security...' : 'Pay Now ↗';
  if (spinEl) spinEl.style.display = on ? 'block' : 'none';
}

// ════════════════════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════════════════════
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', attachInterceptor);
} else {
  attachInterceptor();
}