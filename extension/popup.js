// extension/popup.js
'use strict';

const BACKEND = 'http://127.0.0.1:8000';

async function checkBackend() {
  const statusEl = document.getElementById('backend-status');
  const dotEl    = document.getElementById('status-dot');
  try {
    const res  = await fetch(`${BACKEND}/health`, { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    statusEl.textContent = '✅ Online';
    statusEl.style.color = '#4ade80';

    const bEl = document.getElementById('block-val');
    const vEl = document.getElementById('verify-val');
    if (bEl && data.block_threshold)  bEl.textContent = Math.round(data.block_threshold  * 100) + '%';
    if (vEl && data.verify_threshold) vEl.textContent = Math.round(data.verify_threshold * 100) + '%';
  } catch {
    statusEl.textContent = '❌ Offline — start uvicorn';
    statusEl.style.color = '#f87171';
    dotEl.style.background = '#ef4444';
    dotEl.style.boxShadow  = '0 0 6px #ef4444';
  }
}

// Check current tab for the banking page
async function checkPageStatus() {
  const pageEl = document.getElementById('page-status');
  if (!pageEl) return;
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return;
    const result = await chrome.scripting.executeScript({
      target : { tabId: tab.id },
      func   : () => !!window.fraudInterceptorReady,
    });
    const active = result?.[0]?.result;
    pageEl.textContent = active ? '✅ Injected' : '⏳ Not detected';
    pageEl.style.color = active ? '#4ade80' : '#fbbf24';
  } catch {
    pageEl.textContent = 'N/A';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  checkBackend();
  checkPageStatus();
});