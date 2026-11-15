const APP = {
  name: 'Mr & Miss Fresh 2026',
  event: 'Freshers Night',
  date: 'December 4, 2026',
  pricePerVote: 100,
  accountName: 'Miebai Joy Oyindobra',
  accountNumber: '6527209550',
  bankName: 'Moniepoint MFB',
  contact: 'Contact the event team if you need help.'
};

const firebaseConfig = window.FIREBASE_CONFIG || {};
function firebaseConfigured(cfg = firebaseConfig) {
  return cfg.apiKey && !String(cfg.apiKey).startsWith('YOUR_') && cfg.projectId && !String(cfg.projectId).startsWith('YOUR_');
}

let db = null;
let auth = null;
let firebaseReady = false;
try {
  if (firebaseConfigured()) {
    firebase.initializeApp(firebaseConfig);
    db = firebase.firestore();
    auth = firebase.auth();
    firebaseReady = true;
  }
} catch (error) {
  console.warn('Firebase could not be initialized', error);
}

const fallbackNominees = {
  'MR & MISS FRESH 2026': []
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}
function normalize(value) { return String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, ' ').replace(/\s+/g, ' ').trim(); }
function safeId(value) { return normalize(value).replace(/\s+/g, '_').slice(0, 120); }
function initials(name) { return String(name || 'U').trim().split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase() || 'U'; }
function avatarDataUri(name) {
  const hue = Math.abs([...String(name)].reduce((sum, ch) => sum * 31 + ch.charCodeAt(0), 7)) % 360;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640"><rect width="640" height="640" rx="96" fill="hsl(${hue} 72% 38%)"/><text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle" font-family="Arial,sans-serif" font-size="210" font-weight="700" fill="white">${escapeHtml(initials(name))}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
function showToast(message, type = 'success') {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div'); toast.id = 'toast';
    toast.className = 'fixed bottom-5 left-1/2 -translate-x-1/2 z-50 max-w-md rounded-xl px-5 py-3 text-sm shadow-lg';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = `fixed bottom-5 left-1/2 -translate-x-1/2 z-50 max-w-md rounded-xl px-5 py-3 text-sm shadow-lg ${type === 'error' ? 'bg-red-700 text-white' : 'bg-emerald-700 text-white'}`;
  clearTimeout(showToast.timer); showToast.timer = setTimeout(() => toast.remove(), 5000);
}
function formatDate(value) {
  if (!value) return '—';
  const date = typeof value.toDate === 'function' ? value.toDate() : new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
}
async function ensureAnonymousAuth() {
  if (!firebaseReady || !auth) return null;
  if (auth.currentUser) return auth.currentUser;
  try { await auth.signInAnonymously(); } catch (error) { console.warn('Anonymous auth unavailable', error); }
  return auth.currentUser || null;
}
async function loadElection() {
  if (!firebaseReady) return { status: 'active', categories: Object.keys(fallbackNominees) };
  const snap = await db.collection('settings').doc('event').get();
  const data = snap.exists ? snap.data() : {};
  return { status: data.status === 'closed' ? 'closed' : 'active', categories: Array.isArray(data.categories) && data.categories.length ? data.categories : Object.keys(fallbackNominees) };
}
async function loadNominees() {
  if (!firebaseReady) return Object.entries(fallbackNominees).flatMap(([category, names]) => names.map(name => ({ id: `${safeId(category)}__${safeId(name)}`, name, category, votes: 0 })));
  const snap = await db.collection('nominees').orderBy('category').get();
  return snap.docs.map(doc => ({ id: doc.id, ...doc.data() }));
}
function accountDetails() {
  return { name: APP.accountName, number: APP.accountNumber, bank: APP.bankName };
}
function requireAdmin() {
  if (!firebaseReady || !auth?.currentUser) { window.location.href = 'login.html?admin=1'; return false; }
  return true;
}
window.APP = APP;
window.appState = { db: () => db, auth: () => auth, firebaseReady: () => firebaseReady };
window.appUtils = { escapeHtml, normalize, safeId, avatarDataUri, showToast, formatDate, ensureAnonymousAuth, loadElection, loadNominees, accountDetails, requireAdmin };
