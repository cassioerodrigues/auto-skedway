// ========================================
// Auto Skedway — Frontend App
// ========================================

// State
const state = {
  executions: [],
  accounts: [],
  sortOrder: 'newest',
  accountFilter: '',
  selectedExecution: null,
  activeRuns: {},
};

// DOM cache
const $ = (id) => document.getElementById(id);

// ========================================
// API Functions
// ========================================

async function api(path, options = {}) {
  // Add API_PREFIX if running under /skedway/
  const fullPath = (window.API_PREFIX || '') + path;
  const res = await fetch(fullPath, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

const fetchExecutions = () => api('/api/executions' + (state.accountFilter ? `?account_id=${state.accountFilter}` : ''));
const fetchExecutionDetails = (ts) => api(`/api/executions/${ts}`);
const fetchAccounts = () => api('/api/accounts');
const fetchStatus = () => api('/api/status');
const createAccount = (data) => api('/api/accounts', { method: 'POST', body: JSON.stringify(data) });
const updateAccount = (id, data) => api(`/api/accounts/${id}`, { method: 'PUT', body: JSON.stringify(data) });
const deleteAccount = (id) => api(`/api/accounts/${id}`, { method: 'DELETE' });
const triggerRun = (id) => api(`/api/accounts/${id}/run`, { method: 'POST' });
const createSchedule = (accountId, data) => api(`/api/accounts/${accountId}/schedules`, { method: 'POST', body: JSON.stringify(data) });
const deleteSchedule = (accountId, schedId) => api(`/api/accounts/${accountId}/schedules/${schedId}`, { method: 'DELETE' });
const updateScheduleApi = (accountId, schedId, data) => api(`/api/accounts/${accountId}/schedules/${schedId}`, { method: 'PUT', body: JSON.stringify(data) });
const deleteExecution = (ts) => api(`/api/executions/${ts}`, { method: 'DELETE' });

// ========================================
// Tab Navigation
// ========================================

function initTabs() {
  document.querySelectorAll('.tab-nav__btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-nav__btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach((c) => c.classList.remove('active'));
      btn.classList.add('active');
      $(`tab-${btn.dataset.tab}`).classList.add('active');

      if (btn.dataset.tab === 'accounts') loadAccountsList();
      if (btn.dataset.tab === 'schedules') loadSchedulesList();
      if (btn.dataset.tab === 'dashboard') loadDashboard();
    });
  });
}

// ========================================
// Dashboard
// ========================================

async function loadDashboard() {
  try {
    const [executions, accounts] = await Promise.all([fetchExecutions(), fetchAccounts()]);
    state.executions = executions;
    state.accounts = accounts;
    renderExecutions(executions);
    renderAccountStatusCards(accounts);
    populateAccountFilter(accounts);
    pollStatus();
  } catch (e) {
    console.error('Dashboard load error:', e);
  }
}

function formatDate(isoString) {
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'short', timeStyle: 'medium' }).format(new Date(isoString));
}

function formatDuration(seconds) {
  if (!seconds) return '-';
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
}

function getStatusBadge(result, execution) {
  // Check if execution is in progress
  if (execution?.status === 'in_progress') {
    return `<span class="badge badge--warning"><span class="badge__dot loading__spinner loading__spinner--xs"></span>Em Andamento</span>`;
  }
  
  const map = {
    dry_run_success: { label: 'Dry Run', cls: 'success' },
    success: { label: 'Sucesso', cls: 'success' },
    login_failed: { label: 'Falha Login', cls: 'error' },
    failure: { label: 'Falha', cls: 'error' },
    timeout: { label: 'Timeout', cls: 'error' },
    error: { label: 'Erro', cls: 'error' },
  };
  const s = map[result] || { label: result || 'Desconhecido', cls: 'warning' };
  return `<span class="badge badge--${s.cls}"><span class="badge__dot"></span>${s.label}</span>`;
}

function formatNextRun(isoString) {
  if (!isoString) return '-';
  const dt = new Date(isoString);
  const dateStr = dt.toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' });
  const timeStr = dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  return `${dateStr} ${timeStr}`;
}

function populateAccountFilter(accounts) {
  const sel = $('accountFilter');
  const val = sel.value;
  sel.innerHTML = '<option value="">All Accounts</option>';
  accounts.forEach((a) => {
    sel.innerHTML += `<option value="${a.id}">${a.label}</option>`;
  });
  sel.value = val;
}

function renderAccountStatusCards(accounts) {
  const container = $('accountStatusCards');
  if (!accounts.length) {
    container.innerHTML = '<p class="empty-hint">No accounts configured. Go to Accounts tab to add one.</p>';
    return;
  }
  container.innerHTML = accounts.map((a) => {
    const running = state.activeRuns[a.id]?.status === 'running';
    const statusCls = a.enabled ? 'active' : 'disabled';
    return `
      <div class="account-card account-card--${statusCls}">
        <div class="account-card__header">
          <span class="account-card__label">${a.label}</span>
          <span class="badge badge--${a.enabled ? 'success' : 'warning'}">${a.enabled ? 'Active' : 'Inactive'}</span>
        </div>
        <div class="account-card__info">
          <span>Desks: ${(a.preferences?.desks || []).join(', ') || '-'}</span>
          <span>Credentials: ${a.has_credentials ? '✓' : '✗'}</span>
          <span>Next Run: ${formatNextRun(a.next_run)}</span>
        </div>
        <button class="btn btn--sm ${running ? 'btn--loading' : 'btn--accent'}" 
                onclick="handleRunNow('${a.id}')" ${running || !a.enabled ? 'disabled' : ''}>
          ${running ? '<span class="loading__spinner loading__spinner--sm"></span> Running...' : '▶ Run Now'}
        </button>
      </div>
    `;
  }).join('');
}

function renderExecutions(executions) {
  const list = $('executionsList');
  if (!executions.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-state__icon">📋</div><div class="empty-state__title">No Executions</div></div>`;
    updateStats([]);
    return;
  }
  const sorted = [...executions].sort((a, b) => {
    // In-progress executions first, then by date
    const aInProgress = a.status === 'in_progress' ? 0 : 1;
    const bInProgress = b.status === 'in_progress' ? 0 : 1;
    if (aInProgress !== bInProgress) return aInProgress - bInProgress;
    
    const ta = new Date(a.execution_time), tb = new Date(b.execution_time);
    return state.sortOrder === 'newest' ? tb - ta : ta - tb;
  });
  list.innerHTML = sorted.map((e) => {
    const accountLabel = state.accounts.find((a) => a.id === e.account_id)?.label || e.account_id || '-';
    return `
      <div class="execution-card" onclick="showExecutionDetails(${JSON.stringify(e).replace(/"/g, '&quot;')})">
        <div class="execution-card__header">
          <div>
            <div class="execution-card__title">${formatDate(e.execution_time)}</div>
            <div class="execution-card__time">${accountLabel}</div>
          </div>
          ${getStatusBadge(e.result, e)}
        </div>
        <div class="execution-card__details">
          <div class="execution-detail"><div class="execution-detail__label">Target Date</div><div class="execution-detail__value">${e.target_date || '-'}</div></div>
          <div class="execution-detail"><div class="execution-detail__label">Desk</div><div class="execution-detail__value">${e.booked_desk || '-'}</div></div>
          <div class="execution-detail"><div class="execution-detail__label">Duration</div><div class="execution-detail__value">${formatDuration(e.duration_seconds)}</div></div>
          <div class="execution-detail"><div class="execution-detail__label">Screenshots</div><div class="execution-detail__value">${e.screenshots || 0}</div></div>
        </div>
        <div class="execution-card__footer">
          <div class="execution-card__screenshot-count">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><path d="M21 15l-5-5L5 21"></path></svg>
            ${e.screenshots || 0} images
          </div>
          <div class="execution-card__actions">
            <button class="btn btn--xs btn--danger" onclick="event.stopPropagation(); handleDeleteExecution('${e.timestamp}')" title="Delete">🗑</button>
            <div class="execution-card__arrow">→</div>
          </div>
        </div>
      </div>`;
  }).join('');
  updateStats(executions);
}

function updateStats(executions) {
  $('totalExecutions').textContent = executions.length;
  $('successCount').textContent = executions.filter((e) => ['dry_run_success', 'success'].includes(e.result)).length;
  $('failureCount').textContent = executions.filter((e) => ['login_failed', 'failure', 'error', 'timeout'].includes(e.result)).length;
  $('loadingStatus').textContent = '✓ Loaded';
}

async function handleRunNow(accountId) {
  try {
    await triggerRun(accountId);
    state.activeRuns[accountId] = { status: 'running' };
    renderAccountStatusCards(state.accounts);
    pollStatus();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

let _pollTimer = null;
async function pollStatus() {
  try {
    const status = await fetchStatus();
    state.activeRuns = status.active_runs || {};
    renderAccountStatusCards(state.accounts);
    
    const hasRunning = Object.values(state.activeRuns).some((r) => r.status === 'running');
    
    // Refresh executions to show in-progress ones in real-time
    if (hasRunning) {
      state.executions = await fetchExecutions();
      renderExecutions(state.executions);
    }
    
    if (hasRunning && !_pollTimer) {
      _pollTimer = setInterval(pollStatus, 3000);
    } else if (!hasRunning && _pollTimer) {
      clearInterval(_pollTimer);
      _pollTimer = null;
      // Refresh executions when run completes
      state.executions = await fetchExecutions();
      renderExecutions(state.executions);
    }
  } catch (e) {
    console.error('Poll error:', e);
  }
}

// ========================================
// Execution Detail Modal
// ========================================

async function showExecutionDetails(execution) {
  state.selectedExecution = execution;
  const details = await fetchExecutionDetails(execution.timestamp);
  if (!details) return;

  $('modalTitle').textContent = `Execution from ${formatDate(execution.execution_time)}`;

  const rc = ['dry_run_success', 'success'].includes(execution.result) ? 'summary-item__value--success'
    : ['login_failed', 'failure', 'error'].includes(execution.result) ? 'summary-item__value--error' : 'summary-item__value--warning';

  $('summaryGrid').innerHTML = `
    <div class="summary-item"><div class="summary-item__label">Resultado</div><div class="summary-item__value ${rc}">${execution.result}</div></div>
    <div class="summary-item"><div class="summary-item__label">Conta</div><div class="summary-item__value">${execution.account_id || '-'}</div></div>
    <div class="summary-item"><div class="summary-item__label">Data Alvo</div><div class="summary-item__value">${execution.target_date || '-'}</div></div>
    <div class="summary-item"><div class="summary-item__label">Mesa Agendada</div><div class="summary-item__value">${execution.booked_desk || '-'}</div></div>
    <div class="summary-item"><div class="summary-item__label">Desks Attempted</div><div class="summary-item__value">${(execution.desks_attempted || []).join(', ') || '-'}</div></div>
    <div class="summary-item"><div class="summary-item__label">Duration</div><div class="summary-item__value">${formatDuration(execution.duration_seconds)}</div></div>
  `;

  // Screenshots
  const sc = $('screenshotsContainer');
  if (!details.screenshot_files?.length) {
    sc.innerHTML = '<p class="empty-hint">No screenshots available</p>';
  } else {
    sc.innerHTML = details.screenshot_files.map((f) => {
      const url = (window.API_PREFIX || '') + `/api/executions/${execution.timestamp}/screenshots/${f}`;
      return `<div class="screenshot-item" onclick="openScreenshotModal('${url}','${f}')"><img src="${url}" alt="${f}" loading="lazy" /><div class="screenshot-item__label">${f}</div></div>`;
    }).join('');
  }

  $('executionLog').textContent = details.execution_log || 'Log not available';
  $('summaryJson').textContent = JSON.stringify(execution, null, 2);

  $('detailsModal').classList.add('active');
  setupToggleButtons();
}

function openScreenshotModal(url, filename) {
  let modal = $('screenshotModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'screenshotModal';
    modal.className = 'screenshot-modal';
    modal.innerHTML = `<div class="screenshot-modal__content"><img id="screenshotImage" class="screenshot-modal__image" /><button class="screenshot-modal__close">×</button></div>`;
    document.body.appendChild(modal);
    modal.querySelector('.screenshot-modal__close').onclick = () => modal.classList.remove('active');
    modal.onclick = (e) => { if (e.target === modal) modal.classList.remove('active'); };
  }
  $('screenshotImage').src = url;
  modal.classList.add('active');
}

function setupToggleButtons() {
  const logBtn = $('toggleLogBtn');
  const jsonBtn = $('toggleJsonBtn');
  if (logBtn) logBtn.onclick = () => toggleLog('executionLog');
  if (jsonBtn) jsonBtn.onclick = () => toggleLog('summaryJson');
}

function toggleLog(logId) {
  const el = $(logId);
  el.classList.toggle('log-collapsed');
  el.classList.toggle('log-expanded');
}

function closeModal(modalId) {
  $(modalId).classList.remove('active');
}

async function confirmDeleteExecution() {
  if (!state.selectedExecution) return;
  const ts = state.selectedExecution.timestamp;
  if (!confirm(`Delete this execution and all screenshots?\n\n${ts}`)) return;
  try {
    await deleteExecution(ts);
    closeModal('detailsModal');
    state.executions = await fetchExecutions();
    renderExecutions(state.executions);
  } catch (e) {
    alert(`Error deleting: ${e.message}`);
  }
}

async function handleDeleteExecution(ts) {
  if (!confirm(`Delete this execution and all screenshots?\n\n${ts}`)) return;
  try {
    await deleteExecution(ts);
    state.executions = await fetchExecutions();
    renderExecutions(state.executions);
  } catch (e) {
    alert(`Error deleting: ${e.message}`);
  }
}

// ========================================
// Accounts Management
// ========================================

async function loadAccountsList() {
  try {
    state.accounts = await fetchAccounts();
    renderAccountsList(state.accounts);
  } catch (e) {
    console.error('Error loading accounts:', e);
  }
}

function renderAccountsList(accounts) {
  const list = $('accountsList');
  if (!accounts.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-state__icon">👤</div><div class="empty-state__title">No Accounts</div><div class="empty-state__text">Click "New Account" to add one</div></div>`;
    return;
  }
  list.innerHTML = accounts.map((a) => `
    <div class="account-item">
      <div class="account-item__main">
        <div class="account-item__header">
          <span class="account-item__label">${a.label}</span>
          ${getStatusBadge(a.enabled ? 'success' : 'warning')}
        </div>
        <div class="account-item__meta">
          <span>ID: <code>${a.id}</code></span>
          <span>Desks: ${(a.preferences?.desks || []).join(', ') || '-'}</span>
          <span>Time: ${a.preferences?.start_time || '08:30'} - ${a.preferences?.end_time || '17:00'}</span>
          <span>Days Ahead: ${a.preferences?.days_ahead ?? 7}</span>
          <span>Credentials: ${a.has_credentials ? '✓ Configured' : '✗ Not configured'}</span>
        </div>
        <div class="account-item__schedules">
          ${(a.schedules || []).map((s) => `
            <span class="schedule-tag ${s.enabled ? '' : 'schedule-tag--disabled'}">
              <code>${s.cron}</code> ${s.description ? `— ${s.description}` : ''}
            </span>
          `).join('') || '<span class="empty-hint">No schedules</span>'})
        </div>
      </div>
      <div class="account-item__actions">
        <button class="btn btn--sm btn--ghost" onclick="editAccount('${a.id}')">Edit</button>
        <button class="btn btn--sm btn--danger" onclick="confirmDeleteAccount('${a.id}', '${a.label}')">Delete</button>
      </div>
    </div>
  `).join('');
}

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
  $('accountUser').placeholder = account ? 'Deixe vazio para manter' : 'email@volvo.com';
  $('accountPasswd').placeholder = account ? 'Deixe vazio para manter' : '••••••••';
  $('accountModal').classList.add('active');
}

async function editAccount(id) {
  const acc = state.accounts.find((a) => a.id === id);
  showAccountModal(acc);
}

async function confirmDeleteAccount(id, label) {
  if (confirm(`Are you sure you want to delete the account "${label}"?`)) {
    try {
      await deleteAccount(id);
      loadAccountsList();
      loadDashboard();
    } catch (e) {
      alert(`Error: ${e.message}`);
    }
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
  };
  const user = $('accountUser').value;
  const passwd = $('accountPasswd').value;
  if (user) data.user = user;
  if (passwd) data.passwd = passwd;

  try {
    if (id) {
      await api(`/api/accounts/${id}`, { method: 'PUT', body: JSON.stringify(data) });
    } else {
      await createAccount(data);
    }
    closeModal('accountModal');
    loadAccountsList();
    loadDashboard();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

// ========================================
// Schedules Management
// ========================================

async function loadSchedulesList() {
  try {
    state.accounts = await fetchAccounts();
    renderSchedulesList(state.accounts);
  } catch (e) {
    console.error('Error loading schedules:', e);
  }
}

function renderSchedulesList(accounts) {
  const list = $('schedulesList');
  const allSchedules = [];
  accounts.forEach((a) => {
    (a.schedules || []).forEach((s) => {
      allSchedules.push({ ...s, accountId: a.id, accountLabel: a.label });
    });
  });

  // Add schedule button
  const headerHtml = `
    <div class="section-header" style="margin-bottom: 1rem;">
      <span>${allSchedules.length} agendamento(s)</span>
      <button class="btn btn--primary btn--sm" onclick="showScheduleModal()">
        + Novo Agendamento
      </button>
    </div>
  `;

  if (!allSchedules.length) {
    list.innerHTML = headerHtml + `<div class="empty-state"><div class="empty-state__icon">⏰</div><div class="empty-state__title">Nenhum Agendamento</div><div class="empty-state__text">Adicione um agendamento para executar automaticamente</div></div>`;
    return;
  }

  list.innerHTML = headerHtml + allSchedules.map((s) => `
    <div class="schedule-item ${s.enabled ? '' : 'schedule-item--disabled'}">
      <div class="schedule-item__main">
        <div class="schedule-item__header">
          <span class="schedule-item__cron"><code>${s.cron}</code></span>
          ${s.description ? `<span class="schedule-item__desc">${s.description}</span>` : ''}
          ${getStatusBadge(s.enabled ? 'success' : 'warning')}
        </div>
        <div class="schedule-item__meta">
          <span>Conta: <strong>${s.accountLabel}</strong></span>
          <span>ID: <code>${s.id}</code></span>
        </div>
      </div>
      <div class="schedule-item__actions">
        <button class="btn btn--sm btn--ghost" onclick="toggleScheduleEnabled('${s.accountId}','${s.id}',${!s.enabled})">
          ${s.enabled ? 'Disable' : 'Enable'}
        </button>
        <button class="btn btn--sm btn--danger" onclick="confirmDeleteSchedule('${s.accountId}','${s.id}')">Delete</button>
      </div>
    </div>
  `).join('');
}

function showScheduleModal() {
  $('scheduleModalTitle').textContent = 'New Schedule';
  $('scheduleFormAccountId').value = '';
  $('scheduleFormId').value = '';
  $('scheduleCron').value = '';
  $('scheduleDescription').value = '';
  $('scheduleEnabled').checked = true;
  // Populate account select
  const sel = $('scheduleAccountSelect');
  sel.innerHTML = state.accounts.map((a) => `<option value="${a.id}">${a.label}</option>`).join('');
  $('scheduleModal').classList.add('active');
}

async function handleScheduleSubmit(e) {
  e.preventDefault();
  const accountId = $('scheduleAccountSelect').value;
  const data = {
    cron: $('scheduleCron').value,
    description: $('scheduleDescription').value,
    enabled: $('scheduleEnabled').checked,
  };
  try {
    await createSchedule(accountId, data);
    closeModal('scheduleModal');
    loadSchedulesList();
  } catch (e) {
    alert(`Erro: ${e.message}`);
  }
}

async function toggleScheduleEnabled(accountId, schedId, enabled) {
  try {
    await updateScheduleApi(accountId, schedId, { enabled });
    loadSchedulesList();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

async function confirmDeleteSchedule(accountId, schedId) {
  if (confirm('Delete this schedule?')) {
    try {
      await deleteSchedule(accountId, schedId);
      loadSchedulesList();
    } catch (e) {
      alert(`Erro: ${e.message}`);
    }
  }
}

// ========================================
// Event Listeners & Init
// ========================================

function initEventListeners() {
  $('modalCloseBtn').addEventListener('click', () => closeModal('detailsModal'));
  $('detailsModal').querySelector('.modal__backdrop').addEventListener('click', () => closeModal('detailsModal'));
  $('deleteExecutionBtn').addEventListener('click', () => confirmDeleteExecution());
  $('accountModalCloseBtn').addEventListener('click', () => closeModal('accountModal'));
  $('accountModal').querySelector('.modal__backdrop').addEventListener('click', () => closeModal('accountModal'));
  $('accountCancelBtn').addEventListener('click', () => closeModal('accountModal'));
  $('scheduleModalCloseBtn').addEventListener('click', () => closeModal('scheduleModal'));
  $('scheduleModal').querySelector('.modal__backdrop').addEventListener('click', () => closeModal('scheduleModal'));
  $('scheduleCancelBtn').addEventListener('click', () => closeModal('scheduleModal'));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal.active').forEach((m) => m.classList.remove('active'));
    }
  });

  $('refreshBtn').addEventListener('click', loadDashboard);
  $('sortSelect').addEventListener('change', (e) => { state.sortOrder = e.target.value; renderExecutions(state.executions); });
  $('accountFilter').addEventListener('change', async (e) => {
    state.accountFilter = e.target.value;
    state.executions = await fetchExecutions();
    renderExecutions(state.executions);
  });
  $('addAccountBtn').addEventListener('click', () => showAccountModal());
  $('accountForm').addEventListener('submit', handleAccountSubmit);
  $('scheduleForm').addEventListener('submit', handleScheduleSubmit);
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initEventListeners();
  loadDashboard();
});

document.addEventListener('DOMContentLoaded', () => {
  initializeEventListeners();
  loadAndRenderExecutions();
});
