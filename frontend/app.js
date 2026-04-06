// ========================================
// Execution Dashboard - App.js
// ========================================

// State Management
const state = {
  executions: [],
  sortOrder: 'newest',
  selectedExecution: null,
};

// DOM References
const elements = {
  refreshBtn: document.getElementById('refreshBtn'),
  executionsList: document.getElementById('executionsList'),
  detailsModal: document.getElementById('detailsModal'),
  modalCloseBtn: document.getElementById('modalCloseBtn'),
  modalBackdrop: document.querySelector('.modal__backdrop'),
  sortSelect: document.getElementById('sortSelect'),
  totalExecutions: document.getElementById('totalExecutions'),
  successCount: document.getElementById('successCount'),
  failureCount: document.getElementById('failureCount'),
  loadingStatus: document.getElementById('loadingStatus'),
  toggleLogBtn: null,
  toggleJsonBtn: null,
};

// ========================================
// API Functions
// ========================================

/**
 * Fetch all executions from the API
 */
async function fetchExecutions() {
  try {
    const response = await fetch('/api/executions');
    if (!response.ok) throw new Error('Failed to fetch executions');
    return await response.json();
  } catch (error) {
    console.error('Error fetching executions:', error);
    showEmptyState('Erro ao carregar execuções');
    return [];
  }
}

/**
 * Fetch details for a specific execution
 */
async function fetchExecutionDetails(timestamp) {
  try {
    const response = await fetch(`/api/executions/${timestamp}`);
    if (!response.ok) throw new Error('Failed to fetch execution details');
    return await response.json();
  } catch (error) {
    console.error('Error fetching execution details:', error);
    return null;
  }
}

// ========================================
// UI Rendering Functions
// ========================================

/**
 * Format a timestamp to a readable date
 */
function formatDate(isoString) {
  const date = new Date(isoString);
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'medium',
  }).format(date);
}

/**
 * Format duration in seconds to a readable string
 */
function formatDuration(seconds) {
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(0);
  return `${minutes}m ${secs}s`;
}

/**
 * Get status badge HTML
 */
function getStatusBadge(result) {
  const statusMap = {
    dry_run_success: { label: 'Sucesso (Dry Run)', class: 'success' },
    success: { label: 'Sucesso', class: 'success' },
    login_failed: { label: 'Falha de Login', class: 'error' },
    booking_failed: { label: 'Falha ao Agendar', class: 'error' },
    error: { label: 'Erro', class: 'error' },
    warning: { label: 'Aviso', class: 'warning' },
  };

  const status = statusMap[result] || { label: result, class: 'warning' };
  const badgeClass = `execution-card__status execution-card__status--${status.class}`;
  return `
    <span class="${badgeClass}">
      <span class="execution-card__badge"></span>
      ${status.label}
    </span>
  `;
}

/**
 * Get result color class
 */
function getResultColor(result) {
  if (['dry_run_success', 'success'].includes(result)) {
    return 'summary-item__value--success';
  }
  if (['login_failed', 'booking_failed', 'error'].includes(result)) {
    return 'summary-item__value--error';
  }
  return 'summary-item__value--warning';
}

/**
 * Render execution card
 */
function createExecutionCard(execution) {
  const card = document.createElement('div');
  card.className = 'execution-card';
  card.innerHTML = `
    <div class="execution-card__header">
      <div>
        <div class="execution-card__title">Execução de ${formatDate(execution.execution_time)}</div>
        <div class="execution-card__time">${execution.execution_time}</div>
      </div>
      ${getStatusBadge(execution.result)}
    </div>

    <div class="execution-card__details">
      <div class="execution-detail">
        <div class="execution-detail__label">Data Alvo</div>
        <div class="execution-detail__value">${execution.target_date || 'N/A'}</div>
      </div>
      <div class="execution-detail">
        <div class="execution-detail__label">Mesa Agendada</div>
        <div class="execution-detail__value">${execution.booked_desk || 'Nenhuma'}</div>
      </div>
      <div class="execution-detail">
        <div class="execution-detail__label">Duração</div>
        <div class="execution-detail__value">${formatDuration(execution.duration_seconds)}</div>
      </div>
      <div class="execution-detail">
        <div class="execution-detail__label">Screenshots</div>
        <div class="execution-detail__value">${execution.screenshots}</div>
      </div>
    </div>

    <div class="execution-card__footer">
      <div class="execution-card__screenshot-count">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <path d="M21 15l-5-5L5 21"></path>
        </svg>
        ${execution.screenshots} imagens
      </div>
      <div class="execution-card__arrow">→</div>
    </div>
  `;

  card.addEventListener('click', () => showExecutionDetails(execution));
  return card;
}

/**
 * Render all executions
 */
function renderExecutions(executions) {
  elements.executionsList.innerHTML = '';

  if (executions.length === 0) {
    showEmptyState('Nenhuma execução encontrada');
    return;
  }

  // Sort executions
  const sorted = [...executions].sort((a, b) => {
    const timeA = new Date(a.execution_time);
    const timeB = new Date(b.execution_time);
    return state.sortOrder === 'newest' ? timeB - timeA : timeA - timeB;
  });

  // Create and append cards
  sorted.forEach((execution) => {
    const card = createExecutionCard(execution);
    elements.executionsList.appendChild(card);
  });

  // Update stats
  updateStats(executions);
}

/**
 * Show empty state message
 */
function showEmptyState(message) {
  elements.executionsList.innerHTML = `
    <div class="empty-state">
      <div class="empty-state__icon">📋</div>
      <div class="empty-state__title">Nenhuma Execução</div>
      <div class="empty-state__text">${message}</div>
    </div>
  `;
}

/**
 * Update statistics cards
 */
function updateStats(executions) {
  const total = executions.length;
  const success = executions.filter((e) =>
    ['dry_run_success', 'success'].includes(e.result)
  ).length;
  const failures = executions.filter((e) =>
    ['login_failed', 'booking_failed', 'error'].includes(e.result)
  ).length;

  elements.totalExecutions.textContent = total;
  elements.successCount.textContent = success;
  elements.failureCount.textContent = failures;
  elements.loadingStatus.textContent = '✓ Carregado';
}

// ========================================
// Modal Functions
// ========================================

/**
 * Show execution details in modal
 */
async function showExecutionDetails(execution) {
  state.selectedExecution = execution;

  // Fetch full details
  const details = await fetchExecutionDetails(execution.timestamp);
  if (!details) return;

  // Update modal content
  document.getElementById('modalTitle').textContent = `Execução de ${formatDate(execution.execution_time)}`;

  // Render summary grid
  renderSummaryGrid(execution);

  // Render screenshots
  renderScreenshots(execution, details);

  // Render logs
  renderExecutionLog(details);
  renderSummaryJson(execution);

  // Show modal
  elements.detailsModal.classList.add('active');

  // Setup toggle buttons
  setupToggleButtons();
}

/**
 * Render summary grid in modal
 */
function renderSummaryGrid(execution) {
  const summaryGrid = document.getElementById('summaryGrid');
  const resultColor = getResultColor(execution.result);

  summaryGrid.innerHTML = `
    <div class="summary-item">
      <div class="summary-item__label">Resultado</div>
      <div class="summary-item__value ${resultColor}">${execution.result}</div>
    </div>
    <div class="summary-item">
      <div class="summary-item__label">Data Alvo</div>
      <div class="summary-item__value">${execution.target_date || 'N/A'}</div>
    </div>
    <div class="summary-item">
      <div class="summary-item__label">Mesa Agendada</div>
      <div class="summary-item__value">${execution.booked_desk || '-'}</div>
    </div>
    <div class="summary-item">
      <div class="summary-item__label">Mesas Tentadas</div>
      <div class="summary-item__value">${
        execution.desks_attempted.length > 0
          ? execution.desks_attempted.join(', ')
          : '-'
      }</div>
    </div>
    <div class="summary-item">
      <div class="summary-item__label">Duração</div>
      <div class="summary-item__value">${formatDuration(execution.duration_seconds)}</div>
    </div>
    <div class="summary-item">
      <div class="summary-item__label">Timestamp</div>
      <div class="summary-item__value" style="font-size: 0.75rem;">${execution.execution_time}</div>
    </div>
  `;
}

/**
 * Render screenshots gallery
 */
function renderScreenshots(execution, details) {
  const container = document.getElementById('screenshotsContainer');
  container.innerHTML = '';

  if (!details.screenshot_files || details.screenshot_files.length === 0) {
    container.innerHTML = '<p style="color: var(--color-text-secondary); text-align: center;">Nenhuma screenshot disponível</p>';
    return;
  }

  details.screenshot_files.forEach((filename) => {
    const item = document.createElement('div');
    item.className = 'screenshot-item';

    const imageUrl = `/api/executions/${execution.timestamp}/screenshots/${filename}`;

    item.innerHTML = `
      <img src="${imageUrl}" alt="${filename}" loading="lazy" />
      <div class="screenshot-item__label">${filename}</div>
    `;

    item.addEventListener('click', () => openScreenshotModal(imageUrl, filename));
    container.appendChild(item);
  });
}

/**
 * Open screenshot in full-screen modal
 */
function openScreenshotModal(imageUrl, filename) {
  // Create modal if it doesn't exist
  let modal = document.getElementById('screenshotModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'screenshotModal';
    modal.className = 'screenshot-modal';
    modal.innerHTML = `
      <div class="screenshot-modal__content">
        <img id="screenshotImage" class="screenshot-modal__image" src="" alt="" />
        <button class="screenshot-modal__close">×</button>
      </div>
    `;
    document.body.appendChild(modal);

    modal.querySelector('.screenshot-modal__close').addEventListener('click', () => {
      modal.classList.remove('active');
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('active');
      }
    });
  }

  document.getElementById('screenshotImage').src = imageUrl;
  modal.classList.add('active');
}

/**
 * Render execution log
 */
function renderExecutionLog(details) {
  const logElement = document.getElementById('executionLog');
  logElement.textContent = details.execution_log || 'Log não disponível';
}

/**
 * Render summary JSON
 */
function renderSummaryJson(execution) {
  const jsonElement = document.getElementById('summaryJson');
  jsonElement.textContent = JSON.stringify(execution, null, 2);
}

/**
 * Setup toggle buttons for logs
 */
function setupToggleButtons() {
  // Remove old listeners
  elements.toggleLogBtn = document.getElementById('toggleLogBtn');
  elements.toggleJsonBtn = document.getElementById('toggleJsonBtn');

  if (elements.toggleLogBtn) {
    elements.toggleLogBtn.onclick = () => toggleLog('executionLog');
  }

  if (elements.toggleJsonBtn) {
    elements.toggleJsonBtn.onclick = () => toggleLog('summaryJson');
  }
}

/**
 * Toggle log visibility
 */
function toggleLog(logId) {
  const logElement = document.getElementById(logId);
  const btnId = logId === 'executionLog' ? 'toggleLogBtn' : 'toggleJsonBtn';
  const btn = document.getElementById(btnId);

  logElement.classList.toggle('log-collapsed');
  logElement.classList.toggle('log-expanded');
  btn.classList.toggle('expanded');

  if (btn.classList.contains('expanded')) {
    btn.textContent = logId === 'executionLog' ? 'Ocultar Log' : 'Ocultar JSON';
  } else {
    btn.textContent = logId === 'executionLog' ? 'Mostrar Log Completo' : 'Mostrar JSON';
  }

  // Add icon back
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '16');
  svg.setAttribute('height', '16');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '2');
  svg.innerHTML = '<polyline points="6 9 12 15 18 9"></polyline>';

  btn.innerHTML = '';
  btn.appendChild(svg);
  btn.appendChild(
    document.createTextNode(
      btn.classList.contains('expanded')
        ? logId === 'executionLog'
          ? ' Ocultar Log'
          : ' Ocultar JSON'
        : logId === 'executionLog'
          ? ' Mostrar Log Completo'
          : ' Mostrar JSON'
    )
  );
}

/**
 * Close modal
 */
function closeModal() {
  elements.detailsModal.classList.remove('active');
  state.selectedExecution = null;
}

// ========================================
// Event Listeners
// ========================================

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
  // Close modal
  elements.modalCloseBtn.addEventListener('click', closeModal);
  elements.modalBackdrop.addEventListener('click', closeModal);

  // Keyboard close
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && elements.detailsModal.classList.contains('active')) {
      closeModal();
    }
  });

  // Refresh button
  elements.refreshBtn.addEventListener('click', loadAndRenderExecutions);

  // Sort select
  elements.sortSelect.addEventListener('change', (e) => {
    state.sortOrder = e.target.value;
    renderExecutions(state.executions);
  });
}

// ========================================
// Main Loading Function
// ========================================

/**
 * Load and render executions
 */
async function loadAndRenderExecutions() {
  elements.executionsList.innerHTML = `
    <div class="loading">
      <div class="loading__spinner"></div>
      <p>Carregando execuções...</p>
    </div>
  `;

  state.executions = await fetchExecutions();
  renderExecutions(state.executions);
}

// ========================================
// Initialization
// ========================================

document.addEventListener('DOMContentLoaded', () => {
  initializeEventListeners();
  loadAndRenderExecutions();
});
