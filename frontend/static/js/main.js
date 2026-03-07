/**
 * InvoiceIQ — main.js
 * All API communication lives here.
 * Every hardcoded value in the original HTML is now driven by real fetch() calls.
 */

'use strict';

// ─── Auth token — sessionStorage is source of truth, memory is a cache ────────
// FIX: read from sessionStorage immediately so tokens survive page navigation
window._auth = {
  accessToken:  sessionStorage.getItem('access_token'),
  refreshToken: sessionStorage.getItem('refresh_token'),
  user:         null,
};

// ─── Initialise on DOM ready ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  setupMobileMenu();
  setupNotificationBell();
  setupFileUpload();
  setupTableModals();
  setupProcessingAnimation();
  populateSidebar();

  // Page-specific bootstraps
  const page = getCurrentPage();
  if (page === 'dashboard')   bootstrapDashboard();
  if (page === 'history')     bootstrapHistory();
  if (page === 'reports')     bootstrapReports();
  if (page === 'review')      bootstrapReview();
  if (page === 'success')     bootstrapSuccess();
});

// ─── Utility: which page am I on? ────────────────────────────────────────────
function getCurrentPage() {
  const path = window.location.pathname;
  if (path.includes('dashboard'))  return 'dashboard';
  if (path.includes('history'))    return 'history';
  if (path.includes('reports'))    return 'reports';
  if (path.includes('review'))     return 'review';
  if (path.includes('processing')) return 'processing';
  if (path.includes('upload'))     return 'upload';
  if (path.includes('success'))    return 'success';
  return 'login';
}

function getInvoiceId() {
  const params = new URLSearchParams(window.location.search);
  return params.get('id');
}

// ─── Core API fetch wrapper ───────────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  // FIX: always read sessionStorage first — window._auth is null after page reload
  const token = sessionStorage.getItem('access_token') || window._auth.accessToken;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Add CSRF token for non-GET requests
  if (options.method && options.method !== 'GET') {
    const csrf = getCookie('csrftoken');
    if (csrf) headers['X-CSRFToken'] = csrf;
  }

  let response = await fetch(url, { ...options, headers });

  // FIX: check sessionStorage for refresh token, not window._auth (which is null after reload)
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Use the newly saved token from sessionStorage
      headers['Authorization'] = `Bearer ${sessionStorage.getItem('access_token')}`;
      response = await fetch(url, { ...options, headers });
    } else {
      // Refresh failed — clear everything and redirect to login
      sessionStorage.clear();
      window.location.href = '/';
      return null;
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}`);
  }

  // For export endpoints that return files
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('text/csv') ||
     (contentType.includes('application/json') && response.headers.get('content-disposition'))) {
    return response;
  }

  return response.json();
}

async function refreshAccessToken() {
  try {
    // FIX: read refresh token from sessionStorage first — not memory
    const refreshToken = sessionStorage.getItem('refresh_token') || window._auth.refreshToken;
    if (!refreshToken) return false;

    const res = await fetch('/api/auth/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (res.ok) {
      const data = await res.json();
      // Save new access token back to BOTH sessionStorage and memory
      sessionStorage.setItem('access_token', data.access);
      window._auth.accessToken = data.access;
      return true;
    }
  } catch (e) {}
  return false;
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

// ─── LOGIN ────────────────────────────────────────────────────────────────────
async function handleLoginSubmit(e) {
  e.preventDefault();

  const email    = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const btn      = document.querySelector('.sign-in-button');

  btn.textContent = 'Signing in…';
  btn.disabled = true;

  try {
    const response = await fetch('/api/auth/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) throw new Error('Invalid credentials. Check your email and password.');

    const data = await response.json();

    // Store tokens in sessionStorage so they survive page navigation
    sessionStorage.setItem('access_token',  data.access);
    sessionStorage.setItem('refresh_token', data.refresh);
    sessionStorage.setItem('user',          JSON.stringify(data.user));

    // Also keep in memory for current page
    window._auth.accessToken  = data.access;
    window._auth.refreshToken = data.refresh;
    window._auth.user         = data.user;

    window.location.href = '/dashboard/';

  } catch (err) {
    btn.textContent = 'Sign In to Dashboard →';
    btn.disabled = false;

    // Show error inside the form (more visible than toast on login page)
    const errorBox = document.getElementById('login-error');
    if (errorBox) {
      errorBox.textContent = '❌ ' + (err.message || 'Login failed. Check your email and password.');
      errorBox.style.display = 'block';
    } else {
      showToast(err.message || 'Login failed.', 'error');
    }
  }
}

// ─── SIDEBAR — populate with real user data ───────────────────────────────────
async function populateSidebar() {
  const storedUser = sessionStorage.getItem('user');
  if (!storedUser) return;

  let user;
  try { user = JSON.parse(storedUser); } catch (e) { return; }

  // User profile elements in sidebar
  document.querySelectorAll('.sidebar-user-name').forEach(el => el.textContent = user.full_name || '');
  document.querySelectorAll('.sidebar-user-role').forEach(el => {
    el.textContent = user.role ? (user.role.charAt(0).toUpperCase() + user.role.slice(1)) : '';
  });
  document.querySelectorAll('.sidebar-user-avatar').forEach(el => el.textContent = user.avatar_initials || '');

  // Top nav avatar
  document.querySelectorAll('.user-avatar').forEach(el => el.textContent = user.avatar_initials || '');

  // Storage bar
  const used  = user.storage_used_gb  || 0;
  const limit = user.storage_limit_gb || 1;
  const pct   = Math.min(Math.round((used / limit) * 100), 100);

  document.querySelectorAll('.progress-fill').forEach(el => el.style.width = pct + '%');
  document.querySelectorAll('.storage-text').forEach(el => {
    el.innerHTML = `${used} GB <span style="opacity:0.8">of ${limit} GB</span>`;
  });
}

// ─── NOTIFICATIONS ────────────────────────────────────────────────────────────
async function loadNotifications() {
  try {
    const data = await apiFetch('/api/auth/notifications/');
    if (!data) return;

    const dropdown = document.querySelector('.notification-dropdown');
    const badge    = document.querySelector('.notification-badge');

    if (badge) {
      badge.style.display = data.unread_count > 0 ? 'block' : 'none';
    }

    if (!dropdown) return;

    if (data.notifications.length === 0) {
      dropdown.innerHTML = `<div class="notification-item" style="color:var(--text-light);text-align:center;padding:20px;">
        No new notifications
      </div>`;
      return;
    }

    const TYPE_COLORS = {
      invoice_processed: '#10B981',
      review_required:   '#F59E0B',
      invoice_flagged:   '#EF4444',
      invoice_approved:  '#10B981',
      invoice_rejected:  '#6B7280',
      system:            '#6B7280',
    };

    dropdown.innerHTML = data.notifications.map(n => `
      <div class="notification-item" style="border-left: 3px solid ${TYPE_COLORS[n.type] || '#ccc'};"
           onclick="markNotificationRead(${n.id}, this)">
        <div class="notification-title">${n.title}</div>
        <div class="notification-time">${n.time_ago}</div>
        ${n.invoice_id ? `<a href="/review/?id=${n.invoice_id}" style="font-size:11px;color:var(--primary);font-weight:600;">Open →</a>` : ''}
      </div>
    `).join('');

  } catch (err) {
    console.warn('Could not load notifications:', err);
  }
}

async function markNotificationRead(id, el) {
  try {
    await apiFetch(`/api/auth/notifications/${id}/`, { method: 'PATCH' });
    el.style.opacity = '0.5';
  } catch (err) {}
}

// ─── DASHBOARD ────────────────────────────────────────────────────────────────
async function bootstrapDashboard() {
  // Redirect to login if no token in sessionStorage
  const token = sessionStorage.getItem('access_token');
  if (!token) { window.location.href = '/'; return; }

  try {
    const data = await apiFetch('/api/reports/dashboard/');
    if (!data) return;

    // KPI cards
    _setText('[data-kpi="invoices_this_month"]', data.kpis.invoices_this_month);
    _setText('[data-kpi="pending_review"]',       data.kpis.pending_review);
    _setText('[data-kpi="processed_today"]',      data.kpis.processed_today);
    _setText('[data-kpi="cost_saved"]',           `KSH ${(data.kpis.cost_saved_usd || 0).toLocaleString()}`);

    // Recent invoices table
    const tbody = document.querySelector('[data-recent-invoices]');
    if (tbody) {
      if (data.recent_invoices.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-light);font-size:13px;">
          No invoices yet. <a href="/upload/" style="color:var(--primary);font-weight:600;">Upload your first invoice →</a>
        </td></tr>`;
      } else {
        const STATUS_ICONS = {
          approved:       `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="10" height="10"><polyline points="20 6 9 17 4 12"/></svg>`,
          pending_review: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="10" height="10"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
          flagged:        `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="10" height="10"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>`,
          rejected:       `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="10" height="10"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
          processing:     `<span class="spin-sm"></span>`,
        };
        const CONF_ICONS = {
          high:   `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="9" height="9"><polyline points="20 6 9 17 4 12"/></svg>`,
          medium: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="9" height="9"><line x1="5" y1="12" x2="19" y2="12"/></svg>`,
          low:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="9" height="9"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/></svg>`,
        };
        const getInitials = name => (name || '—').split(' ').slice(0,2).map(w=>w[0]).join('').toUpperCase();
        tbody.innerHTML = data.recent_invoices.map(inv => `
          <tr>
            <td>
              <div class="vendor-cell">
                <div class="vendor-initials">${getInitials(inv.vendor_name)}</div>
                <div>
                  <div class="vendor-name-text">${inv.vendor_name || '—'}
                    ${_isToday(inv.uploaded_at) ? `<span class="new-badge" style="margin-left:5px;">NEW</span>` : ''}
                  </div>
                  ${inv.ai_flag_message ? `<div class="flag-dot" style="margin-top:3px;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="9" height="9"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>AI Flag</div>` : ''}
                </div>
              </div>
            </td>
            <td class="inv-mono" data-label="Invoice No.">${inv.invoice_number || '—'}</td>
            <td style="color:var(--text-light);font-size:12px;" data-label="Date">${inv.invoice_date || '—'}</td>
            <td class="amount-cell" data-label="Amount">KSH ${_formatAmount(inv.total_amount)}</td>
            <td data-label="Status">
              <span class="s-pill ${inv.status}">
                ${STATUS_ICONS[inv.status] || ''}
                ${inv.display_status}
              </span>
            </td>
            <td data-label="Confidence">
              <span class="conf-pill ${inv.confidence_level}">
                ${CONF_ICONS[inv.confidence_level] || ''}
                ${inv.confidence_level === 'high' ? 'High' : inv.confidence_level === 'medium' ? 'Medium' : 'Low'}
              </span>
            </td>
            <td>
              <a href="/review/?id=${inv.id}" class="tbl-action">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="12" height="12"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                View
              </a>
            </td>
          </tr>
        `).join('');
      }
    }

    // Greeting
    _setText('.nav-greeting', `Good ${_timeOfDay()}, ${data.user.full_name.split(' ')[0]}`);

    loadNotifications();

  } catch (err) {
    console.error('Dashboard load error:', err);
    showToast('Could not load dashboard data', 'error');
  }
}

// ─── UPLOAD ───────────────────────────────────────────────────────────────────
async function handleProcessInvoice(e) {
  e.preventDefault();

  const fileInput = document.querySelector('[data-file-input]');
  if (!fileInput || !fileInput.files[0]) {
    showToast('Please select a file first', 'error');
    return;
  }

  const btn = document.querySelector('.process-button');
  btn.textContent = 'Uploading…';
  btn.disabled = true;

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  try {
    // FIX: read from sessionStorage first
    const token = sessionStorage.getItem('access_token') || window._auth.accessToken;
    if (!token) { window.location.href = '/'; return; }

    const headers = { 'Authorization': `Bearer ${token}` };
    const csrf = getCookie('csrftoken');
    if (csrf) headers['X-CSRFToken'] = csrf;

    const response = await fetch('/api/invoices/upload/', {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || 'Upload failed');
    }

    const data = await response.json();
    const invoiceId = data.invoice_id;

    // Show processing modal instead of navigating away
    const modal = document.getElementById('processingModal');
    if (modal) {
      modal.classList.add('active');
      _pollProcessingModal(invoiceId);
    } else {
      // Fallback: old behaviour
      window.location.href = `/processing/?id=${invoiceId}`;
    }

  } catch (err) {
    btn.textContent = 'Process Invoice';
    btn.disabled = false;
    showToast(err.message || 'Upload failed. Please try again.', 'error');
  }
}



// ─── PROCESSING MODAL — poll while staying on upload page ─────────────────────
async function _pollProcessingModal(invoiceId) {
  const percentText = document.getElementById('modalProgressPercent');
  const barFill     = document.getElementById('modalBarFill');
  const titleEl     = document.getElementById('modalTitle');

  // SVG icons for each step state (check for done, spinner for active, circle for pending)
  const ICON_CHECK   = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
  const ICON_SPIN    = `<svg class="spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`;
  const ICON_PENDING = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/></svg>`;

  // Step-specific base icons (shown when pending)
  const STEP_ICONS = {
    1: `<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
    2: `<svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`,
    3: `<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>`,
    4: `<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>`,
  };

  const STATUS_LABELS = {
    pending:   'Pending',
    active:    'Processing…',
    completed: 'Complete',
  };

  let pollInterval = setInterval(async () => {
    try {
      const data = await apiFetch(`/api/invoices/${invoiceId}/status/`);
      if (!data) return;

      const progress = data.processing_progress || 0;

      // Update percent + bar
      if (percentText) percentText.textContent = progress + '%';
      if (barFill)     barFill.style.width = progress + '%';

      // Update steps
      const stepData = data.step_labels || {};
      for (let i = 1; i <= 4; i++) {
        const stepEl   = document.querySelector(`[data-modal-step="${i}"]`);
        if (!stepEl) continue;
        const iconWrap = stepEl.querySelector('.pm-step-icon');
        const statusEl = stepEl.querySelector('.pm-step-status');

        stepEl.classList.remove('step-pending', 'step-active', 'step-completed');

        if (stepData[i] && stepData[i].done) {
          stepEl.classList.add('step-completed');
          if (iconWrap) iconWrap.innerHTML = ICON_CHECK;
          if (statusEl) statusEl.textContent = STATUS_LABELS.completed;
        } else if (i === data.processing_current_step) {
          stepEl.classList.add('step-active');
          if (iconWrap) iconWrap.innerHTML = ICON_SPIN;
          if (statusEl) statusEl.textContent = STATUS_LABELS.active;
        } else {
          stepEl.classList.add('step-pending');
          if (iconWrap) iconWrap.innerHTML = STEP_ICONS[i] || ICON_PENDING;
          if (statusEl) statusEl.textContent = STATUS_LABELS.pending;
        }
      }

      // Done
      if (data.status === 'pending_review' || progress >= 100) {
        clearInterval(pollInterval);
        if (titleEl)     titleEl.textContent     = 'Ready for Review';
        if (percentText) percentText.textContent = '100%';
        if (barFill)     barFill.style.width     = '100%';
        setTimeout(() => { window.location.href = `/review/?id=${invoiceId}`; }, 700);
        return;
      }

      if (data.processing_error) {
        clearInterval(pollInterval);
        showToast('Processing issue — opening review page', 'warning');
        setTimeout(() => { window.location.href = `/review/?id=${invoiceId}`; }, 1500);
      }

    } catch (err) {
      console.warn('Modal poll error:', err);
    }
  }, 2000);

  // Safety redirect after 60s
  setTimeout(() => {
    clearInterval(pollInterval);
    window.location.href = `/review/?id=${invoiceId}`;
  }, 60000);
}

function handleCancelProcessing() {
  if (confirm('Cancel processing? You will need to re-upload the file.')) {
    const modal = document.getElementById('processingModal');
    if (modal) modal.classList.remove('active');
    const btn = document.querySelector('.process-button');
    if (btn) {
      btn.textContent = 'Process Invoice';
      btn.disabled = false;
    }
    // Reset file input
    const fileInput = document.querySelector('[data-file-input]');
    if (fileInput) fileInput.value = '';
    const dropZone = document.querySelector('[data-drop-zone]');
    if (dropZone) dropZone.dispatchEvent(new Event('reset'));
  }
}

// ─── PROCESSING — poll for real progress ─────────────────────────────────────
function setupProcessingAnimation() {
  const processingPage = document.querySelector('[data-processing-page]');
  if (!processingPage) return;

  const invoiceId = getInvoiceId();
  if (!invoiceId) {
    _runMockProcessingAnimation();
    return;
  }

  _pollProcessingStatus(invoiceId);
}

async function _pollProcessingStatus(invoiceId) {
  const percentEl = document.getElementById('procPercent') || document.querySelector('.progress-percent');
  const barFill   = document.getElementById('procBarFill');
  const titleEl   = document.getElementById('procTitle');

  const ICON_CHECK = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
  const ICON_SPIN  = `<svg class="spin-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`;

  const STEP_ICONS = {
    1: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
    2: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`,
    3: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>`,
    4: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>`,
  };

  let pollInterval = setInterval(async () => {
    try {
      const data = await apiFetch(`/api/invoices/${invoiceId}/status/`);
      if (!data) return;

      const progress = data.processing_progress || 0;
      if (percentEl) percentEl.textContent = progress + '%';
      if (barFill)   barFill.style.width   = progress + '%';

      const stepData = data.step_labels || {};
      for (let i = 1; i <= 4; i++) {
        const stepEl  = document.querySelector(`[data-step="${i}"]`);
        if (!stepEl) continue;
        const dotEl    = stepEl.querySelector('.proc-step-dot');
        const statusEl = stepEl.querySelector('.proc-step-status');

        stepEl.classList.remove('step-pending', 'step-active', 'step-completed');

        if (stepData[i] && stepData[i].done) {
          stepEl.classList.add('step-completed');
          if (dotEl)    dotEl.innerHTML    = ICON_CHECK;
          if (statusEl) statusEl.textContent = 'Complete';
        } else if (i === data.processing_current_step) {
          stepEl.classList.add('step-active');
          if (dotEl)    dotEl.innerHTML    = ICON_SPIN;
          if (statusEl) statusEl.textContent = 'Processing…';
        } else {
          stepEl.classList.add('step-pending');
          if (dotEl)    dotEl.innerHTML    = STEP_ICONS[i] || '';
          if (statusEl) statusEl.textContent = 'Pending';
        }
      }

      if (data.status === 'pending_review' || progress >= 100) {
        clearInterval(pollInterval);
        if (titleEl)   titleEl.textContent   = 'Ready for Review';
        if (percentEl) percentEl.textContent = '100%';
        if (barFill)   barFill.style.width   = '100%';
        setTimeout(() => { window.location.href = `/review/?id=${invoiceId}`; }, 700);
      }

      if (data.processing_error) {
        clearInterval(pollInterval);
        showToast('Processing encountered an issue — please review manually', 'warning');
        setTimeout(() => { window.location.href = `/review/?id=${invoiceId}`; }, 2000);
      }

    } catch (err) {
      console.warn('Polling error:', err);
    }
  }, 2000);

  setTimeout(() => {
    clearInterval(pollInterval);
    window.location.href = `/review/?id=${invoiceId}`;
  }, 60000);
}

function _runMockProcessingAnimation() {
  // Targets the processing page standalone elements
  const percentEl = document.getElementById('procPercent') || document.querySelector('.progress-percent');
  const barFill   = document.getElementById('procBarFill');

  if (!percentEl) return;

  const ICON_CHECK = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
  const ICON_SPIN  = `<svg class="spin-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`;

  // Realistic eased progress — ~55 seconds total, human-paced
  const SEGMENTS = [
    // [targetPercent, durationMs]
    [12,  6000],   // 0–12%  : upload acknowledged
    [30, 14000],   // 12–30% : OCR scanning
    [58, 20000],   // 30–58% : AI extraction — visibly slow
    [78, 12000],   // 58–78% : validation
    [91, 10000],   // 78–91% : preparing review — crawls to near-stop
  ];

  let current = 0;
  let segIndex = 0;
  let segStart = 0;
  let segStartPct = 0;
  let lastTick = performance.now();
  let animId;

  function tick(now) {
    if (segIndex >= SEGMENTS.length) {
      // Stall at 92% — waiting for real API
      if (percentEl) percentEl.textContent = '92%';
      if (barFill)   barFill.style.width   = '92%';
      return;
    }

    const [targetPct, duration] = SEGMENTS[segIndex];
    const elapsed = now - segStart;
    const t = Math.min(elapsed / duration, 1);
    // ease-out cubic: starts fast, decelerates
    const eased = 1 - Math.pow(1 - t, 3);
    current = segStartPct + (targetPct - segStartPct) * eased;

    if (percentEl) percentEl.textContent = Math.floor(current) + '%';
    if (barFill)   barFill.style.width   = current + '%';

    if (t >= 1) {
      segStartPct = targetPct;
      segIndex++;
      segStart = now;
    }

    animId = requestAnimationFrame(tick);
  }

  segStart = performance.now();
  animId = requestAnimationFrame(tick);

  // Step transitions — timed to feel natural alongside the progress
  const STEP_EVENTS = [
    { step: 2, state: 'active',    delay:  4000 },  // OCR starts
    { step: 2, state: 'completed', delay: 19000 },  // OCR done  (~15s of scanning)
    { step: 3, state: 'active',    delay: 19500 },  // AI starts
    { step: 3, state: 'completed', delay: 40000 },  // AI done   (~20s extracting)
    { step: 4, state: 'active',    delay: 40500 },  // Prep starts
    { step: 4, state: 'completed', delay: 51000 },  // Prep done (~10s preparing)
  ];

  STEP_EVENTS.forEach(({ step, state, delay }) => {
    setTimeout(() => {
      // Works for both [data-step] (processing page) and [data-modal-step] (upload modal)
      const el = document.querySelector(`[data-step="${step}"], [data-modal-step="${step}"]`);
      if (!el) return;
      const dotEl    = el.querySelector('.proc-step-dot, .pm-step-icon');
      const statusEl = el.querySelector('.proc-step-status, .pm-step-status');

      el.classList.remove('step-pending', 'step-active', 'step-completed');
      el.classList.add('step-' + state);

      if (dotEl) {
        dotEl.innerHTML = state === 'completed' ? ICON_CHECK : ICON_SPIN;
      }
      if (statusEl) {
        statusEl.textContent = state === 'completed' ? 'Complete' : 'Processing…';
      }
    }, delay);
  });
}

// ─── REVIEW PAGE ──────────────────────────────────────────────────────────────
async function bootstrapReview() {
  const invoiceId = getInvoiceId();
  if (!invoiceId) return;

  try {
    const invoice = await apiFetch(`/api/invoices/${invoiceId}/`);
    if (!invoice) return;

    _setText('[data-invoice-number]', invoice.invoice_number || 'INV-???');
    _setText('[data-vendor-name]',    invoice.vendor_name    || 'Unknown Vendor');

    const summary = invoice.overall_confidence_summary;
    if (summary) {
      _setText('[data-overall-confidence]', `${summary.overall_percent}%`);
      _setWidth('[data-confidence-bar]',    `${summary.overall_percent}%`);
      _setText('[data-fields-high]',        summary.high_count);
      _setText('[data-fields-review]',      summary.needs_review_count);
    }

    const fieldsContainer = document.querySelector('[data-extracted-fields]');
    if (fieldsContainer && invoice.extracted_fields && invoice.extracted_fields.length > 0) {
      fieldsContainer.innerHTML = invoice.extracted_fields.map(field => `
        <div class="field-row confidence-${field.confidence_label}" data-field-name="${field.field_name}">
          <div class="field-label">
            ${field.field_label}
            <span class="confidence-badge confidence-${field.confidence_label}">
              ${field.confidence_percent}%
            </span>
          </div>
          <input
            type="text"
            class="field-input"
            value="${_escAttr(field.effective_value)}"
            data-field="${field.field_name}"
            data-original="${_escAttr(field.extracted_value)}"
            onblur="handleFieldCorrection(this, ${invoiceId})"
          >
          ${field.confidence_label !== 'high' ? `
            <div class="field-warning">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              AI confidence ${field.confidence_percent}% — please verify against the original document
            </div>
          ` : ''}
        </div>
      `).join('');
    }

    const lineItemsTbody = document.querySelector('[data-line-items]');
    if (lineItemsTbody && invoice.line_items && invoice.line_items.length > 0) {
      lineItemsTbody.innerHTML = invoice.line_items.map(item => `
        <tr>
          <td>${item.description}</td>
          <td>${item.quantity}</td>
          <td>${invoice.currency} ${_formatAmount(item.unit_price)}</td>
          <td><strong>${invoice.currency} ${_formatAmount(item.total)}</strong></td>
          <td><span class="confidence-badge confidence-${item.ai_confidence >= 0.85 ? 'high' : 'medium'}">${Math.round(item.ai_confidence * 100)}%</span></td>
        </tr>
      `).join('');
    }

    if (invoice.document_preview_url) {
      const previewContainer = document.querySelector('[data-document-preview]');
      if (previewContainer) {
        const rawUrl = invoice.document_preview_url;
        const isPdf  = rawUrl.toLowerCase().includes('.pdf') || rawUrl.includes('/media/');
        if (isPdf) {
          // Suppress the browser's native PDF toolbar/nav panel/thumbnail sidebar
          const cleanUrl = rawUrl.split('#')[0] + '#toolbar=0&navpanes=0&scrollbar=1&view=FitH&zoom=page-width';
          previewContainer.innerHTML = `
            <iframe
              src="${cleanUrl}"
              style="width:100%;height:100%;border:none;border-radius:10px;display:block;"
              title="Invoice Document"
            ></iframe>`;
        } else {
          previewContainer.innerHTML = `
            <img
              src="${rawUrl}"
              style="width:100%;height:100%;object-fit:contain;border-radius:10px;display:block;"
              alt="Invoice Document"
            >`;
        }
        previewContainer.style.background = '#fff';
        previewContainer.style.alignItems = 'stretch';
        previewContainer.style.justifyContent = 'stretch';
      }
    }

    if (invoice.ai_flag_message) {
      const flagBanner = document.querySelector('[data-flag-message]');
      if (flagBanner) {
        flagBanner.textContent = invoice.ai_flag_message;
        flagBanner.style.display = 'block';
      }
    }

  } catch (err) {
    console.error('Review page load error:', err);
    showToast('Could not load invoice details', 'error');
  }
}

async function handleFieldCorrection(inputEl, invoiceId) {
  const fieldName     = inputEl.dataset.field;
  const newValue      = inputEl.value;
  const originalValue = inputEl.dataset.original;
  if (newValue === originalValue) return;
  try {
    await apiFetch(`/api/invoices/${invoiceId}/`, {
      method: 'PATCH',
      body: JSON.stringify({ [fieldName]: newValue }),
    });
    inputEl.style.borderColor = 'var(--success)';
    setTimeout(() => inputEl.style.borderColor = '', 2000);
  } catch (err) {
    showToast(`Could not save correction for ${fieldName}`, 'error');
    inputEl.value = originalValue;
  }
}

// ─── SUCCESS PAGE ────────────────────────────────────────────────────────────
async function bootstrapSuccess() {
  const invoiceId = getInvoiceId();
  if (!invoiceId) return;

  try {
    const invoice = await apiFetch(`/api/invoices/${invoiceId}/`);
    if (!invoice) return;

    // Populate summary card with real invoice data
    document.querySelectorAll('[data-success-vendor]').forEach(el => {
      el.textContent = invoice.vendor_name || '—';
    });
    document.querySelectorAll('[data-success-invoice-number]').forEach(el => {
      el.textContent = invoice.invoice_number || '—';
    });
    document.querySelectorAll('[data-success-total]').forEach(el => {
      const amount = invoice.total_amount
        ? `${invoice.currency || ''} ${parseFloat(invoice.total_amount).toLocaleString('en-US', {minimumFractionDigits: 2})}`
        : '—';
      el.textContent = amount;
    });

  } catch (err) {
    console.error('Success page load error:', err);
  }
}

// ─── APPROVE ──────────────────────────────────────────────────────────────────
async function handleApproveInvoice(e) {
  if (e) e.preventDefault();
  const invoiceId = getInvoiceId();
  const corrections = {};
  document.querySelectorAll('.field-input').forEach(input => {
    if (input.value !== input.dataset.original) corrections[input.dataset.field] = input.value;
  });
  try {
    await apiFetch(`/api/invoices/${invoiceId}/approve/`, {
      method: 'POST',
      body: JSON.stringify({ corrections }),
    });
    showToast('Invoice approved and saved successfully ✓', 'success');
    setTimeout(() => { window.location.href = `/success/?id=${invoiceId}`; }, 600);
  } catch (err) {
    showToast(err.message || 'Could not approve invoice', 'error');
  }
}

// ─── REJECT ───────────────────────────────────────────────────────────────────
async function handleRejectInvoice(e) {
  if (e) e.preventDefault();
  const invoiceId = getInvoiceId();
  const reason = prompt('Rejection reason (optional):') || '';
  if (!confirm('Reject this invoice? It will be marked as Rejected in Document History.')) return;
  try {
    await apiFetch(`/api/invoices/${invoiceId}/reject/`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
    showToast('Invoice rejected', 'warning');
    setTimeout(() => { window.location.href = '/history/'; }, 800);
  } catch (err) {
    showToast(err.message || 'Could not reject invoice', 'error');
  }
}

// ─── FLAG ─────────────────────────────────────────────────────────────────────
async function handleFlagInvoice(e) {
  if (e) e.preventDefault();
  const invoiceId = getInvoiceId();
  const message = prompt('Describe the issue for the manager:') || 'Flagged for manager review';
  try {
    await apiFetch(`/api/invoices/${invoiceId}/flag/`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
    showToast('Invoice flagged — manager will be notified ⚑', 'warning');
  } catch (err) {
    showToast(err.message || 'Could not flag invoice', 'error');
  }
}

// ─── EXPORT ───────────────────────────────────────────────────────────────────
async function handleExport(invoiceId, format, btn) {
  if (!invoiceId) { showToast('No invoice selected', 'error'); return; }

  const formatMap = {
    csv:   { param: 'csv',   ext: 'csv',  label: 'CSV'   },
    json:  { param: 'json',  ext: 'json', label: 'JSON'  },
    excel: { param: 'excel', ext: 'xlsx', label: 'Excel' },
    pdf:   { param: 'pdf',   ext: 'pdf',  label: 'PDF'   },
  };
  const f = formatMap[format] || formatMap['excel'];

  // btn passed directly from onclick — no activeElement guessing
  const origText = btn ? btn.querySelector('.export-option-text')?.textContent : '';
  if (btn) {
    btn.disabled = true;
    btn.style.opacity = '0.7';
    if (btn.querySelector('.export-option-text')) {
      btn.querySelector('.export-option-text').textContent = `Preparing ${f.label}…`;
    }
  }

  try {
    const token = sessionStorage.getItem('access_token');
    const response = await fetch(
      `/api/invoices/${invoiceId}/export/?export_format=${f.param}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const blob        = await response.blob();
    const disposition = response.headers.get('content-disposition') || '';
    const match       = disposition.match(/filename="?([^"]+)"?/);
    const filename    = match ? match[1] : `invoice_${invoiceId}.${f.ext}`;

    const url = URL.createObjectURL(blob);
    const a   = document.createElement('a');
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast(`${f.label} downloaded successfully ✓`, 'success');
  } catch (err) {
    console.error('Export error:', err);
    showToast(`${f.label} export failed — please try again`, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.style.opacity = '';
      if (btn.querySelector('.export-option-text')) {
        btn.querySelector('.export-option-text').textContent = origText;
      }
    }
  }
}

apps/invoices/services/export_service.py
async function handleSendToAccounting(invoiceId, buttonEl) {
  const orig = buttonEl.textContent;
  buttonEl.textContent = 'Sending…';
  buttonEl.disabled = true;
  try {
    await apiFetch(`/api/invoices/${invoiceId}/send-to-accounting/`, { method: 'POST' });
    buttonEl.textContent = '✓ Sent to Accounting System!';
    buttonEl.style.backgroundColor = 'var(--success)';
    showToast('Invoice sent to accounting system ✓', 'success');
    setTimeout(() => {
      buttonEl.textContent = orig;
      buttonEl.style.backgroundColor = '';
      buttonEl.disabled = false;
    }, 3000);
  } catch (err) {
    buttonEl.textContent = orig;
    buttonEl.disabled = false;
    showToast('Could not send to accounting system', 'error');
  }
}

// ─── HISTORY PAGE ─────────────────────────────────────────────────────────────
async function bootstrapHistory() {
  await loadHistoryTable();

  const searchInput = document.querySelector('[data-search]');
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => loadHistoryTable({ search: searchInput.value }), 350);
    });
  }

  const statusFilter = document.querySelector('[data-status-filter]');
  if (statusFilter) {
    statusFilter.addEventListener('change', () => loadHistoryTable({ status: statusFilter.value }));
  }
}

async function loadHistoryTable(params = {}) {
  const tbody   = document.querySelector('[data-history-table]');
  const emptyEl = document.getElementById('empty-state');
  if (!tbody) return;

  tbody.innerHTML = Array(5).fill(`
    <tr style="opacity:0.4;">
      <td><div style="height:14px;background:#E5E7EB;border-radius:4px;width:80%;"></div></td>
      <td><div style="height:14px;background:#E5E7EB;border-radius:4px;width:60%;"></div></td>
      <td><div style="height:14px;background:#E5E7EB;border-radius:4px;width:70%;"></div></td>
      <td><div style="height:14px;background:#E5E7EB;border-radius:4px;width:50%;"></div></td>
      <td><div style="height:14px;background:#E5E7EB;border-radius:4px;width:60%;"></div></td>
      <td><div style="height:14px;background:#E5E7EB;border-radius:4px;width:40%;"></div></td>
    </tr>
  `).join('');

  try {
    const queryString = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v))
    ).toString();

    const data = await apiFetch(`/api/invoices/${queryString ? '?' + queryString : ''}`);
    if (!data) return;

    const invoices = data.results || data;

    if (invoices.length === 0) {
      tbody.innerHTML = '';
      if (emptyEl) emptyEl.style.display = 'table-row';
      return;
    }

    if (emptyEl) emptyEl.style.display = 'none';

    tbody.innerHTML = invoices.map(inv => `
      <tr data-invoice-id="${inv.id}">
        <td>
          <span style="font-weight:600;">${inv.vendor_name || '—'}</span>
          ${inv.ai_flag_message ? `<span style="margin-left:6px;font-size:10px;padding:2px 6px;background:#FEF3C7;color:#92400E;border-radius:4px;">⚠ AI Flag</span>` : ''}
        </td>
        <td style="font-family:monospace;font-size:13px;">${inv.invoice_number || '—'}</td>
        <td>${inv.invoice_date || '—'}</td>
        <td><strong>${inv.currency || ''} ${_formatAmount(inv.total_amount)}</strong></td>
        <td><span class="status-badge status-${inv.status}">${inv.display_status}</span></td>
        <td>
          <span class="confidence-badge confidence-${inv.confidence_level}">
            ${inv.confidence_level === 'high' ? '✓ High' :
              inv.confidence_level === 'medium' ? '~ Medium' : '⚠ Low'}
          </span>
        </td>
        <td class="action-cell">
          <div class="action-dropdown">
            <a href="/review/?id=${inv.id}" class="action-btn-view">View</a>
            <div class="export-dropdown">
              <button class="export-dropdown-toggle" onclick="toggleExportMenu(this)">Export ▾</button>
              <div class="export-dropdown-menu">
                <button class="export-dropdown-item" onclick="handleHistoryExport(this, 'excel')">
                  <span class="item-icon">📊</span> Excel (.xlsx)
                </button>
                <button class="export-dropdown-item" onclick="handleHistoryExport(this, 'pdf')">
                  <span class="item-icon">📄</span> PDF
                </button>
              </div>
            </div>
          </div>
        </td>
      </tr>
    `).join('');

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:20px;color:red;">
      Failed to load invoices: ${err.message}
    </td></tr>`;
  }
}

// ─── REPORTS PAGE ─────────────────────────────────────────────────────────────
async function bootstrapReports() {
  try {
    const data = await apiFetch('/api/reports/business/');
    if (!data) return;

    const fmt = (n, currency) => {
      if (n == null) return '—';
      const num = parseFloat(n);
      if (currency) return `${currency} ${num.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0})}`;
      return num.toLocaleString();
    };

    // ── KPI cards ──
    const currency = data.currency || '';
    _setText('[data-kpi="total_spend"]',      fmt(data.kpis.total_spend_this_month, currency));
    _setText('[data-kpi="pending_count"]',    data.kpis.pending_count ?? '0');
    _setText('[data-kpi="due_soon_amount"]',  fmt(data.kpis.due_soon_amount, currency));
    _setText('[data-kpi="flagged_count"]',    data.kpis.flagged_count ?? '0');

    // Spend change vs last month
    const spendChEl = document.querySelector('[data-kpi-change="spend_change"]');
    if (spendChEl && data.kpis.spend_change_pct != null) {
      const pct = parseFloat(data.kpis.spend_change_pct);
      const sign = pct > 0 ? '↑' : pct < 0 ? '↓' : '→';
      const cls  = pct > 0 ? 'kpi-change-up' : pct < 0 ? 'kpi-change-down' : 'kpi-change-neutral';
      spendChEl.innerHTML = `<span class="${cls}">${sign} ${Math.abs(pct).toFixed(1)}% vs last month</span>`;
    }

    // Oldest pending age
    const pendingAgeEl = document.querySelector('[data-kpi-change="pending_age"]');
    if (pendingAgeEl) {
      const oldest = data.kpis.oldest_pending_days;
      if (oldest != null && oldest > 0) {
        const cls = oldest >= 3 ? 'kpi-change-up' : 'kpi-change-neutral';
        pendingAgeEl.innerHTML = `<span class="${cls}">Oldest waiting ${oldest} day${oldest !== 1 ? 's' : ''}</span>`;
      } else {
        pendingAgeEl.innerHTML = `<span class="kpi-change-neutral">All up to date</span>`;
      }
    }

    // Due soon count
    const dueSoonEl = document.querySelector('[data-kpi-change="due_soon_count"]');
    if (dueSoonEl) {
      const count = data.kpis.due_soon_count || 0;
      dueSoonEl.innerHTML = `<span class="${count > 0 ? 'kpi-change-up' : 'kpi-change-neutral'}">${count} invoice${count !== 1 ? 's' : ''} due within 7 days</span>`;
    }

    // Flagged desc
    const flaggedDescEl = document.querySelector('[data-kpi-change="flagged_desc"]');
    const flaggedLinkEl = document.querySelector('[data-flagged-link]');
    if (flaggedDescEl) {
      const count = data.kpis.flagged_count || 0;
      flaggedDescEl.innerHTML = count > 0
        ? `<span class="kpi-change-up">Need your attention</span>`
        : `<span class="kpi-change-neutral">Nothing flagged</span>`;
    }
    if (flaggedLinkEl) {
      flaggedLinkEl.style.display = (data.kpis.flagged_count > 0) ? 'inline-block' : 'none';
    }

    // ── Attention banner ──
    _renderAlertBanner(data.alerts || [], currency);

    // ── Spend chart ──
    _renderSpendChart(data.monthly_spend || [], currency);

    // ── Pipeline ──
    _renderPipeline(data.pipeline || {});

    // ── Upcoming payments ──
    _renderUpcomingPayments(data.upcoming_payments || [], currency);

    // ── Vendor spend ──
    _renderVendorSpend(data.vendor_spend || [], currency);

  } catch (err) {
    console.error('Reports load error:', err);
    showToast('Could not load reports data', 'error');
  }
}

function _renderAlertBanner(alerts, currency) {
  const banner = document.querySelector('[data-alert-banner]');
  const list   = document.querySelector('[data-alert-list]');
  if (!banner || !list || !alerts.length) return;

  const dotClass = { danger: 'alert-dot-red', warning: 'alert-dot-orange', info: 'alert-dot-blue' };

  list.innerHTML = alerts.map(a => `
    <div class="alert-item">
      <div class="alert-item-left">
        <div class="alert-dot ${dotClass[a.level] || 'alert-dot-orange'}"></div>
        <span class="alert-text">${a.message}</span>
      </div>
      ${a.link ? `<a href="${a.link}" class="alert-link">${a.action || 'Review →'}</a>` : ''}
    </div>
  `).join('');

  banner.classList.add('has-alerts');
}

function _renderSpendChart(monthlySpend, currency) {
  const container = document.querySelector('[data-spend-chart]');
  if (!container) return;

  if (!monthlySpend.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">📈</div>No spend data yet</div>';
    return;
  }

  const maxAmt = Math.max(...monthlySpend.map(d => parseFloat(d.total) || 0), 1);
  const now = new Date();
  const currentMonthStr = now.toLocaleString('default', { month: 'short' }).toUpperCase();

  container.innerHTML = `
    <div style="display:flex;align-items:flex-end;gap:8px;height:100%;width:100%;padding-bottom:24px;position:relative;">
      ${monthlySpend.map(d => {
        const amt   = parseFloat(d.total) || 0;
        const pct   = Math.max((amt / maxAmt) * 140, 4);
        const isCur = d.month.toUpperCase().includes(currentMonthStr);
        const label = amt >= 1000000
          ? `${currency} ${(amt/1000000).toFixed(1)}M`
          : amt >= 1000
          ? `${currency} ${(amt/1000).toFixed(0)}K`
          : `${currency} ${amt.toFixed(0)}`;
        return `
          <div class="spend-bar-wrap">
            <span class="spend-bar-amount">${label}</span>
            <div class="spend-bar ${isCur ? 'current-month' : ''}" style="height:${pct}px;"></div>
            <span class="spend-bar-label">${d.month}</span>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function _renderPipeline(pipeline) {
  const container = document.querySelector('[data-pipeline]');
  if (!container) return;

  const stages = [
    { key: 'processing',     label: 'Processing',      icon: '⚙️' },
    { key: 'pending_review', label: 'Awaiting Approval', icon: '👁️' },
    { key: 'approved',       label: 'Approved',         icon: '✅' },
    { key: 'rejected',       label: 'Rejected',         icon: '❌' },
  ];

  container.innerHTML = stages.map(s => {
    const count   = pipeline[s.key] || 0;
    const ageKey  = `${s.key}_oldest_days`;
    const oldest  = pipeline[ageKey] || 0;
    let ageHtml   = '';
    if (oldest > 0 && (s.key === 'pending_review' || s.key === 'processing')) {
      const cls = oldest >= 3 ? 'pipeline-age-danger' : oldest >= 1 ? 'pipeline-age-warning' : 'pipeline-age';
      ageHtml = `<div class="${cls}">Oldest: ${oldest}d ago</div>`;
    }
    return `
      <div class="pipeline-stage">
        <div style="font-size:22px;margin-bottom:6px;">${s.icon}</div>
        <div class="pipeline-count">${count}</div>
        <div class="pipeline-label">${s.label}</div>
        ${ageHtml}
      </div>
    `;
  }).join('');
}

function _renderUpcomingPayments(payments, currency) {
  const container = document.querySelector('[data-upcoming-payments]');
  if (!container) return;

  if (!payments.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div>No upcoming payments — all clear!</div>';
    return;
  }

  const today = new Date(); today.setHours(0,0,0,0);

  container.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Vendor</th>
          <th>Invoice</th>
          <th>Amount</th>
          <th>Due Date</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        ${payments.map(p => {
          const due     = new Date(p.due_date); due.setHours(0,0,0,0);
          const daysLeft = Math.round((due - today) / 86400000);
          const dueCls   = daysLeft <= 1 ? 'due-urgent' : daysLeft <= 3 ? 'due-soon' : 'due-normal';
          const dueLabel = daysLeft < 0
            ? `Overdue by ${Math.abs(daysLeft)}d`
            : daysLeft === 0 ? 'Due today'
            : daysLeft === 1 ? 'Due tomorrow'
            : `In ${daysLeft} days`;
          const pillCls  = p.status === 'approved' ? 'pill-approved' : p.status === 'flagged' ? 'pill-flagged' : 'pill-pending';
          const pillLabel = p.status === 'approved' ? '✓ Approved' : p.status === 'flagged' ? '⚠ Flagged' : '⏳ Pending';
          const amt = parseFloat(p.total_amount || 0).toLocaleString('en-US', {minimumFractionDigits: 2});
          return `
            <tr>
              <td style="font-weight:600;">${p.vendor_name || '—'}</td>
              <td style="font-family:monospace;font-size:12px;">${p.invoice_number || '—'}</td>
              <td style="font-weight:700;">${currency} ${amt}</td>
              <td class="${dueCls}">${dueLabel}</td>
              <td><span class="status-pill ${pillCls}">${pillLabel}</span></td>
              <td><a href="/review/?id=${p.id}" style="font-size:12px;font-weight:700;color:var(--primary);text-decoration:none;">Review →</a></td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  `;
}

function _renderVendorSpend(vendors, currency) {
  const container = document.querySelector('[data-vendor-spend]');
  if (!container) return;

  if (!vendors.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">🏢</div>No vendor data this month yet</div>';
    return;
  }

  const maxSpend = Math.max(...vendors.map(v => parseFloat(v.this_month) || 0), 1);

  container.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Vendor</th>
          <th>This Month</th>
          <th>vs Last Month</th>
          <th style="width:120px;">Share of Spend</th>
          <th>Invoices</th>
        </tr>
      </thead>
      <tbody>
        ${vendors.map(v => {
          const thisMonth  = parseFloat(v.this_month)  || 0;
          const lastMonth  = parseFloat(v.last_month)  || 0;
          const changePct  = lastMonth > 0 ? ((thisMonth - lastMonth) / lastMonth) * 100 : null;
          const changeHtml = changePct == null
            ? '<span style="color:var(--text-light);">New</span>'
            : changePct > 10
            ? `<span class="vendor-change-up">↑ ${changePct.toFixed(0)}%</span>`
            : changePct < -10
            ? `<span class="vendor-change-down">↓ ${Math.abs(changePct).toFixed(0)}%</span>`
            : `<span class="vendor-change-same">≈ Stable</span>`;
          const barPct   = Math.round((thisMonth / maxSpend) * 100);
          const amtLabel = thisMonth >= 1000000
            ? `${currency} ${(thisMonth/1000000).toFixed(2)}M`
            : `${currency} ${thisMonth.toLocaleString('en-US', {minimumFractionDigits: 0})}`;
          return `
            <tr>
              <td style="font-weight:600;">${v.vendor_name}</td>
              <td style="font-weight:700;">${amtLabel}</td>
              <td>${changeHtml}</td>
              <td>
                <div class="spend-bar-inline">
                  <div class="spend-fill-inline" style="width:${barPct}%;"></div>
                </div>
              </td>
              <td style="color:var(--text-light);">${v.invoice_count || 0}</td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  `;
}

function handleExportReport() {
  showToast('Preparing Excel export…', 'success');
  window.open('/api/reports/export/?format=excel', '_blank');
}

// ─── NAVIGATION helpers ───────────────────────────────────────────────────────
function handleProcessAnother(e) {
  if (e) e.preventDefault();
  window.location.href = '/upload/';
}

function handleViewHistory(e) {
  if (e) e.preventDefault();
  window.location.href = '/history/';
}

function handleLogout(e) {
  if (e) e.preventDefault();
  const refreshToken = sessionStorage.getItem('refresh_token');
  const accessToken  = sessionStorage.getItem('access_token');
  if (refreshToken) {
    fetch('/api/auth/logout/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ refresh: refreshToken }),
    }).catch(() => {});
  }
  sessionStorage.clear();
  window._auth = { accessToken: null, refreshToken: null, user: null };
  window.location.href = '/';
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────
function setupMobileMenu() {
  const hamburger = document.querySelector('.hamburger');
  const sidebar   = document.querySelector('.sidebar');
  if (hamburger && sidebar) {
    hamburger.addEventListener('click', () => sidebar.classList.toggle('hidden'));
    document.querySelectorAll('.sidebar-nav a').forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 768) sidebar.classList.add('hidden');
      });
    });
  }
}

function setupNotificationBell() {
  const bell     = document.querySelector('[data-notification-bell]');
  const dropdown = document.querySelector('.notification-dropdown');
  if (bell && dropdown) {
    bell.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = dropdown.classList.toggle('active');
      if (isOpen) loadNotifications();
    });
    document.addEventListener('click', () => dropdown.classList.remove('active'));
  }
}

function setupFileUpload() {
  const zone      = document.querySelector('.drag-drop-zone');
  const fileInput = document.querySelector('[data-file-input]');
  const fileCard  = document.querySelector('[data-file-card]');
  if (!zone || !fileInput) return;

  zone.addEventListener('click', () => fileInput.click());
  zone.addEventListener('dragover',  (e) => { e.preventDefault(); zone.classList.add('active'); });
  zone.addEventListener('dragleave', ()  => zone.classList.remove('active'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('active');
    if (e.dataTransfer.files[0]) _handleFileSelect(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) _handleFileSelect(e.target.files[0]);
  });

  function _handleFileSelect(file) {
    const nameEl = document.querySelector('[data-file-name]');
    const sizeEl = document.querySelector('[data-file-size]');
    const btn    = document.querySelector('.process-button');
    if (nameEl) nameEl.textContent = file.name;
    if (sizeEl) sizeEl.textContent = (file.size / 1024 / 1024).toFixed(1) + ' MB • Ready to process';
    if (fileCard) fileCard.classList.remove('hidden');
    if (btn) btn.removeAttribute('disabled');
  }
}

function setupTableModals() {
  const buttons  = document.querySelectorAll('[data-modal-trigger]');
  const modal    = document.querySelector('.modal');
  const closeBtn = document.querySelector('.modal-close');
  if (!buttons.length || !modal) return;
  buttons.forEach(btn => btn.addEventListener('click', (e) => { e.preventDefault(); modal.classList.add('active'); }));
  if (closeBtn) closeBtn.addEventListener('click', () => modal.classList.remove('active'));
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('active'); });
}

function showToast(message, type = 'success') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const icons = { success: '✓', error: '✕', warning: '⚠' };
  toast.innerHTML = `<span class="toast-icon">${icons[type] || '✓'}</span> ${message}`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(20px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Keyboard shortcuts for review page
document.addEventListener('keydown', (event) => {
  if (getCurrentPage() !== 'review') return;
  if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
  if (event.ctrlKey || event.metaKey) return;
  if (event.key.toLowerCase() === 'a') handleApproveInvoice(event);
  if (event.key.toLowerCase() === 'r') handleRejectInvoice(event);
  if (event.key.toLowerCase() === 'f') handleFlagInvoice(event);
});

// ─── Pure utility functions ───────────────────────────────────────────────────
function _setText(selector, value) {
  document.querySelectorAll(selector).forEach(el => { el.textContent = value; });
}
function _setWidth(selector, value) {
  document.querySelectorAll(selector).forEach(el => { el.style.width = value; });
}
function _formatAmount(amount) {
  if (!amount) return '—';
  return parseFloat(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function _escAttr(str) {
  return String(str || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function _isToday(dateStr) {
  return new Date(dateStr).toDateString() === new Date().toDateString();
}
function _timeOfDay() {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}