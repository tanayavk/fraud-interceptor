// extension/background.js — Service Worker (Manifest V3)
'use strict';

// Track which tabs have the interceptor active
const activeTabs = new Set();

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete') {
    activeTabs.add(tabId);
  }
});

chrome.tabs.onRemoved.addListener(tabId => {
  activeTabs.delete(tabId);
});

// Listen for messages from content.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'FRAUD_RESULT') {
    console.log('[FraudInterceptor BG] Result:', message.data);
    sendResponse({ ok: true });
  }
  if (message.type === 'PING') {
    sendResponse({ status: 'active', version: '2.0' });
  }
});