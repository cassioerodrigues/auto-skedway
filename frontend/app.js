// ═══════════════════════════════════════════════════════════
// Auto Skedway — Frontend App (redesigned, single-page)
// ═══════════════════════════════════════════════════════════

// ─── State ──────────────────────────────────────────────────
const state = {
  executions: [],
  accounts: [],
  sortOrder: 'newest',
  accountFilter: '',
  selectedExecution: null,
  activeRuns: {},
  isAdmin: false,
  holidays: [],
  holidayFormId: null,
};

const $ = (id) => document.getElementById(id);

// ─── API helpers ─────────────────────────────────────────────
async function api(path, options = {}) {
  const fullPath = (window.API_PREFIX || '') + path;
  const res = await fetch(fullPath, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

const fetchExecutions       = () => api('/api/executions' + (state.accountFilter ? `?account_id=${state.accountFilter}` : ''));
const fetchExecutionDetails = (ts) => api(`/api/executions/${ts}`);
const fetchAccounts         = () => api('/api/accounts');
const fetchStatus           = () => api('/api/status');
const createAccount         = (data) => api('/api/accounts', { method: 'POST', body: JSON.stringify(data) });
const updateAccount         = (id, data) => api(`/api/accounts/${id}`, { method: 'PUT', body: JSON.stringify(data) });
const deleteAccount         = (id) => api(`/api/accounts/${id}`, { method: 'DELETE' });
const triggerRun            = (id) => api(`/api/accounts/${id}/run`, { method: 'POST' });
const createSchedule        = (accountId, data) => api(`/api/accounts/${accountId}/schedules`, { method: 'POST', body: JSON.stringify(data) });
const deleteSchedule        = (accountId, schedId) => api(`/api/accounts/${accountId}/schedules/${schedId}`, { method: 'DELETE' });
const updateScheduleApi     = (accountId, schedId, data) => api(`/api/accounts/${accountId}/schedules/${schedId}`, { method: 'PUT', body: JSON.stringify(data) });
const deleteExecution       = (ts) => api(`/api/executions/${ts}`, { method: 'DELETE' });
const fetchHolidays         = () => api('/api/holidays');
const createHoliday         = (data) => api('/api/holidays', { method: 'POST', body: JSON.stringify(data) });
const updateHolidayApi      = (id, data) => api(`/api/holidays/${id}`, { method: 'PUT', body: JSON.stringify(data) });
const deleteHoliday         = (id) => api(`/api/holidays/${id}`, { method: 'DELETE' });

// ─── Formatters ──────────────────────────────────────────────
function formatDate(isoString) {
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'short', timeStyle: 'medium' }).format(new Date(isoString));
}

function formatDateShort(isoString) {
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(isoString));
}

function formatDuration(seconds) {
  if (!seconds) return '-';
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
}

function formatNextRun(isoString) {
  if (!isoString) return '-';
  const dt = new Date(isoString);
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' +
    dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function getInitials(label) {
  return label.split(/[\s\-_]+/).slice(0, 2).map(w => w[0]?.toUpperCase() || '').join('');
}

function statusClass(result, status) {
  if (status === 'in_progress') return 'in-progress';
  const map = {
    dry_run_success: 'success',
    success: 'success',
    login_failed: 'error',
    failure: 'error',
    timeout: 'error',
    error: 'error',
  };
  return map[result] || 'warning';
}

function statusLabel(result, status) {
  if (status === 'in_progress') return 'Running';
  const map = {
    dry_run_success: 'Dry Run',
    success: 'Success',
    login_failed: 'Login Failed',
    failure: 'Failed',
    timeout: 'Timeout',
    error: 'Error',
  };
  return map[result] || result || 'Unknown';
}

// ─── Load all data ───────────────────────────────────────────
async function loadAll() {
  try {
    const [executions, accounts] = await Promise.all([fetchExecutions(), fetchAccounts()]);
    state.executions = executions;
    state.accounts = accounts;
    renderAccountStatusCards(accounts);
    renderSchedulesList(accounts);
    renderExecutions(executions);
    populateAccountFilter(accounts);
    await pollStatus();
    if (state.isAdmin) await loadHolidays();
  } catch (e) {
    console.error('Load error:', e);
  }
}

function populateAccountFilter(accounts) {
  const sel = $('accountFilter');
  const val = sel.value;
  sel.innerHTML = '<option value="">All accounts</option>';
  accounts.forEach((a) => {
    sel.innerHTML += `<option value="${a.id}">${a.label}</option>`;
  });
  sel.value = val;
}

// ─── Sidebar: Account cards ──────────────────────────────────
function renderAccountStatusCards(accounts) {
  const container = $('accountStatusCards');
  if (!accounts.length) {
    container.innerHTML = `<div class="empty-state" style="padding:20px 10px">
      <span style="font-size:11px">No accounts yet.</span>
    </div>`;
    return;
  }
  container.innerHTML = accounts.map((a) => {
    const running = state.activeRuns[a.id]?.status === 'running';
    const isEnabled = a.enabled !== false;
    return `
    <div class="acct-card ${isEnabled ? 'acct-card--active' : 'acct-card--disabled'}">
      <div class="acct-card__top">
        <div class="acct-card__avatar">${getInitials(a.label)}</div>
        <div class="acct-card__info">
          <div class="acct-card__name" title="${a.label}">${a.label}</div>
          <div class="acct-card__email">${a.user || 'No email set'}</div>
        </div>
        <div class="acct-card__actions">
          <button class="icon-action" onclick="editAccount('${a.id}')" title="Edit">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="icon-action icon-action--danger" onclick="confirmDeleteAccount('${a.id}','${a.label}')" title="Delete">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="acct-card__footer">
        <span style="font-size:10.5px;color:var(--text-3)">Next: ${formatNextRun(a.next_run)}</span>
        <button class="run-btn" onclick="handleRunNow('${a.id}')" ${running || !isEnabled ? 'disabled' : ''}>
          ${running ? '<div class="spinner spinner--xs"></div> Running' : `<svg width="9" height="9" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Now`}
        </button>
      </div>
    </div>`;
  }).join('');
}

// ─── Sidebar: Schedules ──────────────────────────────────────
function renderSchedulesList(accounts) {
  const list = $('schedulesList');
  const all = [];
  accounts.forEach((a) => {
    (a.schedules || []).forEach((s) => all.push({ ...s, accountId: a.id, accountLabel: a.label }));
  });

  if (!all.length) {
    list.innerHTML = `<div class="empty-state" style="padding:20px 10px">
      <span style="font-size:11px">No schedules yet.</span>
    </div>`;
    return;
  }

  list.innerHTML = all.map((s) => `
    <div class="sched-row ${s.enabled ? '' : 'sched-row--disabled'}">
      <div class="sched-row__dot"></div>
      <div class="sched-row__body">
        <div class="sched-row__name" title="${s.accountLabel}">${s.description || s.accountLabel}</div>
        <div class="sched-row__cron">${s.cron}</div>
      </div>
      <div class="sched-row__actions">
        <button class="icon-action" onclick="toggleScheduleEnabled('${s.accountId}','${s.id}',${!s.enabled})" title="${s.enabled ? 'Disable' : 'Enable'}">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${s.enabled
              ? '<path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/>'
              : '<polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'}
          </svg>
        </button>
        <button class="icon-action" onclick="editSchedule('${s.accountId}','${s.id}')" title="Edit">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
        </button>
        <button class="icon-action icon-action--danger" onclick="confirmDeleteSchedule('${s.accountId}','${s.id}')" title="Delete">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
          </svg>
        </button>
      </div>
    </div>
  `).join('');
}

// ─── Main: Executions feed ───────────────────────────────────
function renderExecutions(executions) {
  const list = $('executionsList');
  if (!executions.length) {
    list.innerHTML = `<div class="empty-state">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-3)">
        <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
      <span>No executions found</span>
    </div>`;
    return;
  }

  const sorted = [...executions].sort((a, b) => {
    const aIP = a.status === 'in_progress' ? 0 : 1;
    const bIP = b.status === 'in_progress' ? 0 : 1;
    if (aIP !== bIP) return aIP - bIP;
    const ta = new Date(a.execution_time), tb = new Date(b.execution_time);
    return state.sortOrder === 'newest' ? tb - ta : ta - tb;
  });

  list.innerHTML = sorted.map((e) => {
    const accountLabel = state.accounts.find((a) => a.id === e.account_id)?.label || e.account_id || '-';
    const cls = statusClass(e.result, e.status);
    const lbl = statusLabel(e.result, e.status);
    const isRunning = e.status === 'in_progress';
    return `
    <div class="exec-row exec-row--${cls}" onclick="showExecutionDetails(${JSON.stringify(e).replace(/"/g, '&quot;')})">
      <div class="exec-row__indicator"></div>
      <div class="exec-row__main">
        <div class="exec-row__title">${accountLabel}</div>
        <div class="exec-row__meta">${e.target_date ? `target ${e.target_date}` : ''}${e.booked_desk ? ` · desk ${e.booked_desk}` : ''}${e.duration_seconds ? ` · ${formatDuration(e.duration_seconds)}` : ''}</div>
      </div>
      <div class="exec-row__right">
        <span class="exec-row__time">${formatDateShort(e.execution_time)}</span>
        <span class="exec-chip exec-chip--${cls}">
          ${isRunning ? '<div class="spinner spinner--xs"></div>' : ''} ${lbl}
        </span>
        ${isRunning ? '' : `<button class="icon-action icon-action--danger" onclick="event.stopPropagation(); confirmDeleteExecutionFromList('${e.timestamp}')" title="Delete execution">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
          </svg>
        </button>`}
      </div>
    </div>`;
  }).join('');
}

// ─── Run now ─────────────────────────────────────────────────
async function handleRunNow(accountId) {
  try {
    await triggerRun(accountId);
    state.activeRuns[accountId] = { status: 'running' };
    renderAccountStatusCards(state.accounts);
    pollStatus();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

// ─── Polling ─────────────────────────────────────────────────
let _pollTimer = null;
let _detailsPollTimer = null;

function applyAdminVisibility() {
  const section = $('holidaysSection');
  if (state.isAdmin) {
    section.removeAttribute('hidden');
  } else {
    section.setAttribute('hidden', '');
  }
}

async function loadHolidays() {
  if (!state.isAdmin) return;
  try {
    const data = await fetchHolidays();
    state.holidays = data.holidays || [];
    renderHolidaysList();
  } catch (e) {
    console.error('Holiday load error:', e);
  }
}

function renderHolidaysList() {
  const list = $('holidaysList');
  if (!state.holidays.length) {
    list.innerHTML = `<div class="empty-state" style="padding:20px 10px">
      <span style="font-size:11px">Nenhum feriado cadastrado.</span>
    </div>`;
    return;
  }
  list.innerHTML = state.holidays.map((h) => {
    const dateParts = h.date.split('-');
    const dateFormatted = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}`;
    return `
    <div class="sched-row">
      <div class="sched-row__dot" style="background:var(--blue)"></div>
      <div class="sched-row__body">
        <div class="sched-row__name" title="${h.description}">${h.description}</div>
        <div class="sched-row__cron">${dateFormatted}</div>
      </div>
      <div class="sched-row__actions">
        <button class="icon-action" onclick="showHolidayModal(${JSON.stringify(h).replace(/"/g, '&quot;')})" title="Editar">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
        </button>
        <button class="icon-action icon-action--danger" onclick="confirmDeleteHoliday('${h.id}')" title="Deletar">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
          </svg>
        </button>
      </div>
    </div>`;
  }).join('');
}

function showHolidayModal(holiday = null) {
  state.holidayFormId = holiday?.id || null;
  $('holidayModalTitle').textContent = holiday ? 'Editar Feriado' : 'Novo Feriado';
  $('holidayDate').value = holiday?.date || '';
  $('holidayDescription').value = holiday?.description || '';
  $('holidayModal').classList.add('open');
}

async function handleHolidaySubmit(e) {
  e.preventDefault();
  const data = {
    date: $('holidayDate').value,
    description: $('holidayDescription').value,
  };
  try {
    if (state.holidayFormId) {
      await updateHolidayApi(state.holidayFormId, data);
    } else {
      await createHoliday(data);
    }
    closeModal('holidayModal');
    await loadHolidays();
  } catch (err) {
    const msg = err.message || '';
    if (msg === 'forbidden' || msg.includes('HTTP 403')) {
      alert('Apenas o admin pode editar feriados');
    } else if (msg.includes('already exists')) {
      alert('Já existe um feriado nessa data');
    } else if (msg.toLowerCase().includes('past') || msg.toLowerCase().includes('invalid date') || msg.includes('HTTP 400')) {
      alert('Data inválida (não pode ser passada)');
    } else {
      alert(`Erro: ${msg}`);
    }
  }
}

async function confirmDeleteHoliday(id) {
  if (!confirm('Deletar este feriado?')) return;
  try {
    await deleteHoliday(id);
    await loadHolidays();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

async function pollStatus() {
  try {
    const status = await fetchStatus();
    state.activeRuns = status.active_runs || {};
    state.isAdmin = status.is_admin || false;
    applyAdminVisibility();
    renderAccountStatusCards(state.accounts);

    const hasRunning = Object.values(state.activeRuns).some((r) => r.status === 'running');

    if (hasRunning) {
      state.executions = await fetchExecutions();
      renderExecutions(state.executions);
    }

    if (hasRunning && !_pollTimer) {
      _pollTimer = setInterval(pollStatus, 3000);
    } else if (!hasRunning && _pollTimer) {
      clearInterval(_pollTimer);
      _pollTimer = null;
      state.executions = await fetchExecutions();
      renderExecutions(state.executions);
    }
  } catch (e) {
    console.error('Poll error:', e);
  }
}

// ─── Detail panel ────────────────────────────────────────────
async function showExecutionDetails(execution) {
  state.selectedExecution = execution;
  if (_detailsPollTimer) { clearInterval(_detailsPollTimer); _detailsPollTimer = null; }

  const details = await fetchExecutionDetails(execution.timestamp);
  if (!details) return;

  $('detailTitle').textContent = `${formatDate(execution.execution_time)}`;

  const cls = statusClass(execution.result, execution.status);

  $('summaryGrid').innerHTML = `
    <div class="summary-item"><div class="summary-item__label">Result</div><div class="summary-item__value text-${cls === 'success' ? 'success' : cls === 'error' ? 'error' : 'warning'}">${statusLabel(execution.result, execution.status)}</div></div>
    <div class="summary-item"><div class="summary-item__label">Account</div><div class="summary-item__value">${execution.account_id || '-'}</div></div>
    <div class="summary-item"><div class="summary-item__label">Target Date</div><div class="summary-item__value">${execution.target_date || '-'}</div></div>
    <div class="summary-item"><div class="summary-item__label">Booked Desk</div><div class="summary-item__value">${execution.booked_desk || '-'}</div></div>
    <div class="summary-item summary-item--wide"><div class="summary-item__label">Desks Attempted</div><div class="summary-item__value">${(execution.desks_attempted || []).join(', ') || '-'}</div></div>
    <div class="summary-item"><div class="summary-item__label">Duration</div><div class="summary-item__value">${formatDuration(execution.duration_seconds)}</div></div>
  `;

  const sc = $('screenshotsContainer');
  if (!details.screenshot_files?.length) {
    sc.innerHTML = '<span class="text-muted" style="font-size:12px">No screenshots</span>';
  } else {
    sc.innerHTML = details.screenshot_files.map((f) => {
      const url = (window.API_PREFIX || '') + `/api/executions/${execution.timestamp}/screenshots/${f}`;
      return `<figure class="screenshot-item" onclick="openScreenshotModal('${url}','${f}')">
        <img src="${url}" alt="${f}" loading="lazy" />
        <figcaption>${f}</figcaption>
      </figure>`;
    }).join('');
  }

  $('executionLog').textContent = details.execution_log || 'Log not available';
  $('summaryJson').textContent = JSON.stringify(execution, null, 2);

  // Ensure log/json start collapsed
  $('executionLog').classList.add('log-collapsed');
  $('summaryJson').classList.add('log-collapsed');
  $('toggleLogBtn').textContent = 'Show';
  $('toggleJsonBtn').textContent = 'Show';

  openPanel();
  setupToggleButtons();

  if (execution.status === 'in_progress') startDetailsPolling(execution.timestamp);
}

function openPanel() {
  $('detailsPanel').classList.add('open');
}

function closePanel() {
  $('detailsPanel').classList.remove('open');
  if (_detailsPollTimer) { clearInterval(_detailsPollTimer); _detailsPollTimer = null; }
}

function openScreenshotModal(url, filename) {
  let modal = $('screenshotModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'screenshotModal';
    modal.style.cssText = 'position:fixed;inset:0;z-index:500;display:flex;align-items:center;justify-content:center;background:rgba(7,11,19,0.9);backdrop-filter:blur(8px);cursor:zoom-out';
    modal.innerHTML = `<img id="screenshotImage" style="max-width:90vw;max-height:90vh;border-radius:8px;border:1px solid var(--border-md)" />`;
    document.body.appendChild(modal);
    modal.addEventListener('click', () => modal.remove());
  }
  $('screenshotImage').src = url;
}

function setupToggleButtons() {
  const logBtn = $('toggleLogBtn');
  const jsonBtn = $('toggleJsonBtn');
  if (logBtn) logBtn.onclick = () => toggleReveal('executionLog', logBtn);
  if (jsonBtn) jsonBtn.onclick = () => toggleReveal('summaryJson', jsonBtn);
}

function toggleReveal(elId, btn) {
  const el = $(elId);
  const collapsed = el.classList.toggle('log-collapsed');
  btn.textContent = collapsed ? 'Show' : 'Hide';
}

async function confirmDeleteExecution() {
  if (!state.selectedExecution) return;
  const ts = state.selectedExecution.timestamp;
  if (!confirm(`Delete this execution and all screenshots?\n\n${ts}`)) return;
  try {
    await deleteExecution(ts);
    closePanel();
    state.executions = await fetchExecutions();
    renderExecutions(state.executions);
  } catch (e) {
    alert(`Error deleting: ${e.message}`);
  }
}

async function confirmDeleteExecutionFromList(ts) {
  if (!confirm(`Delete this execution and all screenshots?\n\n${ts}`)) return;
  try {
    await deleteExecution(ts);
    if (state.selectedExecution?.timestamp === ts) closePanel();
    state.executions = await fetchExecutions();
    renderExecutions(state.executions);
  } catch (e) {
    alert(`Error deleting: ${e.message}`);
  }
}

async function startDetailsPolling(timestamp) {
  if (_detailsPollTimer) clearInterval(_detailsPollTimer);
  _detailsPollTimer = setInterval(async () => {
    try {
      const execution = state.selectedExecution;
      if (!execution || execution.timestamp !== timestamp) {
        clearInterval(_detailsPollTimer); _detailsPollTimer = null; return;
      }
      const details = await fetchExecutionDetails(timestamp);
      if (!details) return;

      if (details.status && details.status !== 'in_progress') {
        clearInterval(_detailsPollTimer); _detailsPollTimer = null;
        state.selectedExecution = { ...state.selectedExecution, ...details };
      }

      const logEl = $('executionLog');
      if (logEl) {
        logEl.textContent = details.execution_log || 'Log not available';
        if (!logEl.classList.contains('log-collapsed')) logEl.scrollTop = logEl.scrollHeight;
      }

      const sc = $('screenshotsContainer');
      if (sc && details.screenshot_files?.length) {
        sc.innerHTML = details.screenshot_files.map((f) => {
          const url = (window.API_PREFIX || '') + `/api/executions/${timestamp}/screenshots/${f}`;
          return `<figure class="screenshot-item" onclick="openScreenshotModal('${url}','${f}')">
            <img src="${url}" alt="${f}" loading="lazy" />
            <figcaption>${f}</figcaption>
          </figure>`;
        }).join('');
      }

      $('summaryJson').textContent = JSON.stringify(details, null, 2);
    } catch (e) {
      console.error('Details polling error:', e);
    }
  }, 2000);
}

// ─── Account modal ───────────────────────────────────────────
function showAccountModal(account = null) {
  $('accountModalTitle').textContent = account ? 'Edit Account' : 'New Account';
  $('accountFormId').value = account?.id || '';
  $('accountLabel').value = account?.label || '';
  $('accountUser').value = '';
  $('accountPasswd').value = '';
  $('accountDesks').value = (account?.preferences?.desks || []).join(', ');
  $('accountDaysAhead').value = account?.preferences?.days_ahead ?? 7;
  $('accountStartTime').value = account?.preferences?.start_time || '08:30';
  $('accountEndTime').value = account?.preferences?.end_time || '17:00';
  $('accountEnabled').checked = account?.enabled ?? true;
  $('accountCaptureScreenshots').checked = account?.preferences?.capture_screenshots ?? true;
  $('accountUser').placeholder = account ? 'Leave blank to keep current' : 'email@company.com';
  $('accountPasswd').placeholder = account ? 'Leave blank to keep current' : '••••••••';
  $('accountModal').classList.add('open');
}

function editAccount(id) {
  const acc = state.accounts.find((a) => a.id === id);
  showAccountModal(acc);
}

async function confirmDeleteAccount(id, label) {
  if (!confirm(`Delete account "${label}"?`)) return;
  try {
    await deleteAccount(id);
    await loadAll();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

async function handleAccountSubmit(e) {
  e.preventDefault();
  const id = $('accountFormId').value;
  const data = {
    label: $('accountLabel').value,
    desks: $('accountDesks').value.split(',').map((d) => d.trim()).filter(Boolean),
    days_ahead: parseInt($('accountDaysAhead').value) || 7,
    start_time: $('accountStartTime').value || '08:30',
    end_time: $('accountEndTime').value || '17:00',
    enabled: $('accountEnabled').checked,
    capture_screenshots: $('accountCaptureScreenshots').checked,
  };
  const user = $('accountUser').value;
  const passwd = $('accountPasswd').value;
  if (user) data.user = user;
  if (passwd) data.passwd = passwd;

  try {
    if (id) {
      await updateAccount(id, data);
    } else {
      await createAccount(data);
    }
    closeModal('accountModal');
    await loadAll();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

// ─── Schedule modal ──────────────────────────────────────────
function showScheduleModal(schedule = null) {
  $('scheduleModalTitle').textContent = schedule ? 'Edit Schedule' : 'New Schedule';
  $('scheduleFormId').value = schedule?.id || '';
  $('scheduleFormAccountId').value = schedule?.accountId || '';
  $('scheduleCron').value = schedule?.cron || '';
  $('scheduleDescription').value = schedule?.description || '';
  $('scheduleEnabled').checked = schedule?.enabled ?? true;
  const sel = $('scheduleAccountSelect');
  sel.innerHTML = state.accounts.map((a) => `<option value="${a.id}">${a.label}</option>`).join('');
  if (schedule) {
    sel.value = schedule.accountId;
    sel.disabled = true;
  } else {
    sel.disabled = false;
  }
  $('scheduleModal').classList.add('open');
}

function editSchedule(accountId, schedId) {
  const account = state.accounts.find(a => a.id === accountId);
  const schedule = (account?.schedules || []).find(s => s.id === schedId);
  if (!schedule) return;
  showScheduleModal({ ...schedule, accountId });
}

async function handleScheduleSubmit(e) {
  e.preventDefault();
  const cronValue = $('scheduleCron').value.trim();
  if (!/^(\S+\s+){4}\S+$/.test(cronValue)) {
    alert('Invalid cron expression. Use 5 fields, e.g. "0 7 * * 1-5".');
    $('scheduleCron').focus();
    return;
  }
  const schedId = $('scheduleFormId').value;
  const accountId = $('scheduleAccountSelect').value;
  const editAccountId = $('scheduleFormAccountId').value;
  const data = {
    cron: cronValue,
    description: $('scheduleDescription').value,
    enabled: $('scheduleEnabled').checked,
  };
  try {
    if (schedId) {
      await updateScheduleApi(editAccountId, schedId, data);
    } else {
      await createSchedule(accountId, data);
    }
    closeModal('scheduleModal');
    await loadAll();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

async function toggleScheduleEnabled(accountId, schedId, enabled) {
  try {
    await updateScheduleApi(accountId, schedId, { enabled });
    await loadAll();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

async function confirmDeleteSchedule(accountId, schedId) {
  if (!confirm('Delete this schedule?')) return;
  try {
    await deleteSchedule(accountId, schedId);
    await loadAll();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

function closeModal(id) {
  $(id).classList.remove('open');
}

// ─── Event listeners ─────────────────────────────────────────
function initEventListeners() {
  // Detail panel
  $('closePanelBtn').addEventListener('click', closePanel);
  $('detailBackdrop').addEventListener('click', closePanel);
  $('deleteExecutionBtn').addEventListener('click', confirmDeleteExecution);

  // Account modal
  $('accountModalCloseBtn').addEventListener('click', () => closeModal('accountModal'));
  $('accountModal').querySelector('.modal__backdrop').addEventListener('click', () => closeModal('accountModal'));
  $('accountCancelBtn').addEventListener('click', () => closeModal('accountModal'));

  // Schedule modal
  $('scheduleModalCloseBtn').addEventListener('click', () => closeModal('scheduleModal'));
  $('scheduleModal').querySelector('.modal__backdrop').addEventListener('click', () => closeModal('scheduleModal'));
  $('scheduleCancelBtn').addEventListener('click', () => closeModal('scheduleModal'));

  // Keyboard
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closePanel();
      document.querySelectorAll('.modal.open').forEach((m) => m.classList.remove('open'));
    }
  });

  // Controls
  $('refreshBtn').addEventListener('click', loadAll);
  $('sortSelect').addEventListener('change', (e) => { state.sortOrder = e.target.value; renderExecutions(state.executions); });
  $('accountFilter').addEventListener('change', async (e) => {
    state.accountFilter = e.target.value;
    state.executions = await fetchExecutions();
    renderExecutions(state.executions);
  });

  // Forms
  $('addAccountBtn').addEventListener('click', () => showAccountModal());
  $('accountForm').addEventListener('submit', handleAccountSubmit);
  $('scheduleForm').addEventListener('submit', handleScheduleSubmit);

  // Holiday modal
  $('newHolidayBtn').addEventListener('click', () => showHolidayModal());
  $('holidayModalCloseBtn').addEventListener('click', () => closeModal('holidayModal'));
  $('holidayModal').querySelector('.modal__backdrop').addEventListener('click', () => closeModal('holidayModal'));
  $('holidayCancelBtn').addEventListener('click', () => closeModal('holidayModal'));
  $('holidayForm').addEventListener('submit', handleHolidaySubmit);
}

// ─── Boot ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  loadAll();
});
