// extension/utils/api.js — shared fetch utility
'use strict';

export const BACKEND_URL = 'http://127.0.0.1:8000/risk';
export const USER_ID     = 'demo_user';
export const TIMEOUT_MS  = 5000;

export async function assessRisk(amount, recipient) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(BACKEND_URL, {
      method  : 'POST',
      headers : { 'Content-Type': 'application/json' },
      body    : JSON.stringify({
        user_id   : USER_ID,
        amount    : parseFloat(amount),
        recipient : String(recipient).trim(),
        timestamp : Date.now() / 1000,
      }),
      signal  : controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}