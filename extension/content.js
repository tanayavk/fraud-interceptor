/**
 * Fraud Interceptor — Content Script v2
 * ========================================
 * Injected into every page matching the manifest's content_scripts.
 *
 * Strategy:
 *   1. Detect the pay button and intercept form submit (capture phase)
 *   2. Call the fraud backend
 *   3. Fire a 'fraudResult' CustomEvent on the document
 *   4. script.js receives the event via waitForExtension() and drives the UI
 *
 * This keeps the extension and the page code cleanly decoupled.
 * The extension NEVER touches the DOM for modals — script.js owns the UI.
 *
 * For non-SecureBank sites: the extension falls back to its own
 * injected modal (modal.css handles styling for that).
 */

'use strict';

const CONFIG = {
  BACKEND_URL : 'http://127.0.0.1:8000/risk',
  USER_ID     : 'demo_user',
  TIMEOUT_MS  : 5000,
};

const SELECTORS = {
  FORM      : '#pay-form',
  PAY_BTN   : '#pay-btn',
  AMOUNT    : '#amount',
  RECIPIENT : '#recipient',
};

let intercepting = false;

/* ── Attach ────────────────────────────────────────────────────── */
function attach() {
  const form = document.querySelector(SELECTORS.FORM);
  if (!form) { setTimeout(attach, 500); return; }

  form.addEventListener('submit', onSubmit, true);  // capture phase — fires first
  console.log('[FraudInterceptor] Attached to #pay-form');
}

async function onSubmit(e) {
  e.preventDefault();
  e.stopImmediatePropagation();

  if (intercepting) return;

  const amount    = parseFloat(document.querySelector(SELECTORS.AMOUNT)?.value || '0');
  const recipient = (document.querySelector(SELECTORS.RECIPIENT)?.value || '').trim();

  if (!recipient || !amount || amount <= 0) {
    // Let script.js handle its own validation — re-fire without capturing
    intercepting = true;
    form_element.removeEventListener('submit', onSubmit, true);
    e.target.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    intercepting = false;
    attach();
    return;
  }

  // Show loading state (extension sets it, script.js also sets it)
  setButtonState(true);

  let riskData;
  try {
    riskData = await callBackend(amount, recipient);
  } catch (err) {
    console.warn('[FraudInterceptor] Backend error — defaulting to VERIFY:', err);
    riskData = {
      risk_score : 0.5,
      action     : 'VERIFY',
      reasons    : ['Security service unreachable. Please verify manually.'],
    };
  }

  setButtonState(false);

  // Check if the page has the SecureBank script loaded (preferred UI handler)
  if (window.fraudInterceptorReady) {
    // Fire the event — script.js will pick it up via waitForExtension()
    document.dispatchEvent(new CustomEvent('fraudResult', {
      detail  : riskData,
      bubbles : false,
    }));
    // Also re-fire submit so script.js's own handler processes it
    // (it's listening with addEventListener, not capturing)
    e.target.dispatchEvent(new Event('submit', { bubbles: true, cancelable: false }));

  } else {
    // Fallback: page has no script.js — show our own injected modal
    showFallbackModal(riskData, amount, recipient);
  }
}

/* ── Backend call ──────────────────────────────────────────────── */
async function callBackend(amount, recipient) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), CONFIG.TIMEOUT_MS);

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
  clearTimeout(timer);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* ── Loading state ─────────────────────────────────────────────── */
function setButtonState(loading) {
  const btn = document.querySelector(SELECTORS.PAY_BTN);
  if (!btn) return;
  btn.disabled = loading;
  const label = btn.querySelector('#btn-text') || btn.querySelector('.btn-label');
  const spinner = btn.querySelector('#btn-spinner') || btn.querySelector('.btn-loader');
  if (label)   label.textContent = loading ? 'Checking security...' : 'Pay Now';
  if (spinner) spinner.style.display = loading ? 'block' : 'none';
  btn.classList.toggle('loading', loading);
}

/* ── Fallback modal (for non-SecureBank pages) ─────────────────── */
function showFallbackModal(data, amount, recipient) {
  const pct    = Math.round(data.risk_score * 100);
  const action = data.action;
  const reasons = data.reasons || [];

  const cfg = {
    ALLOW  : { icon:'✅', cls:'fi-allow',  title:'Transaction Approved',     btnHtml:`<button class="fi-btn fi-btn-success" onclick="fiClose('proceed')">Proceed</button>` },
    VERIFY : { icon:'⚠️', cls:'fi-verify', title:'Verification Recommended', btnHtml:`<button class="fi-btn fi-btn-ghost" onclick="fiClose('cancel')">Cancel</button><button class="fi-btn fi-btn-warning" onclick="fiClose('proceed')">Proceed Anyway</button>` },
    BLOCK  : { icon:'🚫', cls:'fi-block',  title:'Transaction Blocked',      btnHtml:`<button class="fi-btn fi-btn-danger" onclick="fiClose('block')">Understood</button>` },
  };
  const c = cfg[action] || cfg.VERIFY;

  const existing = document.getElementById('fi-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.id = 'fi-overlay';
  overlay.innerHTML = `
    <div id="fi-modal">
      <div id="fi-header" class="${c.cls}">
        <div id="fi-icon">${c.icon}</div>
        <div>
          <div id="fi-title">${c.title}</div>
          <div id="fi-subtitle">₹${parseFloat(amount).toLocaleString('en-IN')} → ${recipient}</div>
        </div>
      </div>
      <div id="fi-body" class="${c.cls}">
        <div class="fi-score-row">
          <div>
            <div class="fi-score-label">Risk Score</div>
            <div class="fi-bar-bg"><div class="fi-bar-fill" style="width:${pct}%"></div></div>
          </div>
          <div class="fi-score-value">${pct}%</div>
        </div>
        ${reasons.length ? `<div class="fi-reasons-label">Flags</div><ul class="fi-reasons">${reasons.map(r=>`<li>${r}</li>`).join('')}</ul>` : ''}
      </div>
      <div id="fi-footer">${c.btnHtml}</div>
    </div>`;

  document.body.appendChild(overlay);

  window.fiClose = function(decision) {
    overlay.remove();
    if (decision === 'proceed') {
      // Re-submit form bypassing intercept
      const form = document.querySelector(SELECTORS.FORM);
      if (form) {
        const fakeSubmit = form.onsubmit;
        form.onsubmit = null;
        form.submit?.();
        form.onsubmit = fakeSubmit;
      }
    }
  };

  if (action === 'VERIFY') {
    overlay.addEventListener('click', e => { if (e.target === overlay) fiClose('cancel'); });
  }
  document.addEventListener('keydown', e => { if (e.key === 'Escape') fiClose('cancel'); }, { once: true });
}

/* ── Init ──────────────────────────────────────────────────────── */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', attach);
} else {
  attach();
}