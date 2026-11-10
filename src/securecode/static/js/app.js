/**
 * SecureCode Frontend Client Application
 * Arquitectura modular reactiva en Vanilla JS
 * Inspirado en ChatGPT y Gemini (Dark/Light Mode, Minimalista, Responsive)
 */

(() => {
  'use strict';

  // --- Estado de la Aplicación ---
  const state = {
    token: localStorage.getItem('securecode_token') || null,
    user: JSON.parse(localStorage.getItem('securecode_user') || 'null') || {
      username: 'Iniciar sesión',
      role: 'Acceso seguro requerido',
      plan: 'Enterprise Academic',
      usedQuota: 4104,
      maxQuota: 20480, // Basado en el análisis de 500 MB de Supabase en el informe ES2
      slaAvailability: '99.5%'
    },
    accessRole: null,
    activeTab: 'evaluator',
    selectedControl: 'GH-001',
    evaluationAbortController: null,
    passwordResetTarget: null,
    adminUsers: [],
    evalHistory: JSON.parse(localStorage.getItem('securecode_history') || '[]'),
    finops: null,
    systemHealth: { status: 'checking', latencyMs: null },
    rules: [
      {
        control_id: 'GH-001',
        name: 'Branch Review Policy',
        description: 'Exige un mínimo de 2 revisiones aprobadas y descarte de revisiones obsoletas en ramas protegidas.',
        short_description: '≥ 2 aprobaciones y descarte de revisiones obsoletas',
        branch_required: true,
        rule_file: 'rules/GH-001.json',
        operators: 'AND(required_review_approvals GTE 2, dismiss_stale_reviews EQ true)'
      },
      {
        control_id: 'GH-002',
        name: 'Default Branch Protection',
        description: 'Exige que la rama por defecto del repositorio cuente con protección de rama habilitada.',
        short_description: 'Protección activa en la rama por defecto',
        branch_required: false,
        rule_file: 'rules/GH-002.json',
        operators: 'protection_enabled EQ true'
      },
      {
        control_id: 'GH-003',
        name: 'Signed Commit Enforcement',
        description: 'Exige que GitHub requiera commits firmados en la rama auditada.',
        short_description: 'Firmas de commits exigidas en la rama auditada',
        branch_required: true,
        rule_file: 'rules/GH-003.json',
        operators: 'required_signatures_enabled EQ true'
      }
    ]
  };

  // --- Inicialización al Cargar el DOM ---
  document.addEventListener('DOMContentLoaded', () => {
    initThemeManager();
    initNavigation();
    initEvaluator();
    initHistory();
    initDashboard();
    initSubscription();
    initAdminConsole();
    initClientSettings();
    initAuthModal();
    syncAuthenticatedUser();
    checkSystemHealth();
    setInterval(checkSystemHealth, 30000);
  });

  // --- Gestor de Temas (Dark / Light / System) ---
  function initThemeManager() {
    const metaTheme = document.querySelector('meta[name="color-scheme"]');
    const toggleBtn = document.getElementById('btnThemeToggle');
    const currentThemeText = document.getElementById('currentThemeText');

    function applyTheme(theme) {
      if (theme === 'dark' || theme === 'light') {
        metaTheme.content = theme;
        localStorage.setItem('color-scheme', theme);
        currentThemeText.textContent = theme === 'dark' ? 'Oscuro' : 'Claro';
      } else {
        metaTheme.content = 'light dark';
        localStorage.removeItem('color-scheme');
        currentThemeText.textContent = 'Sistema';
      }
    }

    const saved = localStorage.getItem('color-scheme') || 'light dark';
    applyTheme(saved);

    toggleBtn.addEventListener('click', () => {
      const current = metaTheme.content;
      if (current === 'light dark') {
        applyTheme('dark');
      } else if (current === 'dark') {
        applyTheme('light');
      } else {
        applyTheme('light dark');
      }
    });
  }

  function applyPersistedTheme(theme) {
    const metaTheme = document.querySelector('meta[name="color-scheme"]');
    const currentThemeText = document.getElementById('currentThemeText');
    if (!metaTheme) return;
    if (theme === 'dark' || theme === 'light') {
      metaTheme.content = theme;
      localStorage.setItem('color-scheme', theme);
      if (currentThemeText) currentThemeText.textContent = theme === 'dark' ? 'Oscuro' : 'Claro';
    } else {
      metaTheme.content = 'light dark';
      localStorage.removeItem('color-scheme');
      if (currentThemeText) currentThemeText.textContent = 'Sistema';
    }
  }

  // --- Configuración persistida de la cuenta ---
  function initClientSettings() {
    const form = document.getElementById('clientSettingsForm');
    if (form) form.addEventListener('submit', saveClientSettings);
    updateSettingsAccess();
  }

  function updateSettingsAccess() {
    const panel = document.getElementById('clientSettingsPanel');
    const notice = document.getElementById('settingsAccessNotice');
    const authenticated = Boolean(state.token && state.accessRole);
    if (panel) panel.hidden = !authenticated;
    if (notice) notice.hidden = authenticated;
  }

  async function loadClientSettings() {
    updateSettingsAccess();
    if (!state.token) return;
    try {
      const res = await fetch('/api/v1/settings', { headers: { 'Authorization': 'Bearer ' + state.token } });
      if (!res.ok) throw new Error('No se pudieron recuperar las preferencias');
      applyClientSettings(await res.json());
    } catch {
      const feedback = document.getElementById('settingsFeedback');
      if (feedback) feedback.textContent = 'No fue posible cargar tus preferencias. Puedes reintentar al guardar.';
    }
  }

  function applyClientSettings(settings) {
    state.clientSettings = settings;
    document.getElementById('settingsRepository').value = settings.default_repository || '';
    document.getElementById('settingsBranch').value = settings.default_branch || 'main';
    document.getElementById('settingsLocale').value = settings.locale || 'es-CL';
    document.getElementById('settingsTimezone').value = settings.timezone || 'America/Santiago';
    document.getElementById('settingsTheme').value = settings.theme || 'system';
    document.getElementById('notifyEvaluationCompleted').checked = Boolean(settings.notify_evaluation_completed);
    document.getElementById('notifyEvaluationFailure').checked = Boolean(settings.notify_evaluation_failure);
    document.getElementById('notifyWeeklyDigest').checked = Boolean(settings.notify_weekly_digest);
    applyPersistedTheme(settings.theme || 'system');

    const repoInput = document.getElementById('repoInput');
    const branchInput = document.getElementById('branchInput');
    if (repoInput && !repoInput.value && settings.default_repository) repoInput.value = settings.default_repository;
    if (branchInput && (!branchInput.value || branchInput.value === 'main') && settings.default_branch) branchInput.value = settings.default_branch;
  }

  async function saveClientSettings(event) {
    event.preventDefault();
    const feedback = document.getElementById('settingsFeedback');
    const button = document.getElementById('btnSaveClientSettings');
    const payload = {
      default_repository: document.getElementById('settingsRepository').value.trim(),
      default_branch: document.getElementById('settingsBranch').value.trim(),
      locale: document.getElementById('settingsLocale').value,
      timezone: document.getElementById('settingsTimezone').value,
      theme: document.getElementById('settingsTheme').value,
      notify_evaluation_completed: document.getElementById('notifyEvaluationCompleted').checked,
      notify_evaluation_failure: document.getElementById('notifyEvaluationFailure').checked,
      notify_weekly_digest: document.getElementById('notifyWeeklyDigest').checked
    };
    if (button) button.disabled = true;
    if (feedback) feedback.textContent = 'Guardando preferencias…';
    try {
      const res = await fetch('/api/v1/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + state.token },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(await getApiError(res, 'No se pudieron guardar las preferencias.'));
      applyClientSettings(await res.json());
      if (feedback) feedback.textContent = 'Preferencias guardadas correctamente.';
    } catch (error) {
      if (feedback) feedback.textContent = error.message;
    } finally {
      if (button) button.disabled = false;
    }
  }

  // --- Navegación entre Vistas ---
  function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item[data-view]');
    const viewPanels = document.querySelectorAll('.view-panel');
    const pageTitle = document.getElementById('pageTitleText');
    const btnNewEval = document.getElementById('btnNewEval');
    const btnToggleSidebar = document.getElementById('btnToggleSidebar');
    const sidebar = document.getElementById('sidebar');

    function switchView(viewId, title) {
      state.activeTab = viewId;
      navItems.forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewId);
      });
      viewPanels.forEach(panel => {
        panel.classList.toggle('active', panel.id === `view-${viewId}`);
      });
      if (title && pageTitle) {
        pageTitle.textContent = title;
      }
      if (window.innerWidth <= 768 && sidebar) {
        sidebar.classList.remove('mobile-open');
      }
    }

    navItems.forEach(item => {
      item.addEventListener('click', () => {
        switchView(item.dataset.view, item.dataset.title);
      });
    });

    if (btnNewEval) {
      btnNewEval.addEventListener('click', () => {
        switchView('evaluator', 'Evaluador de Controles');
        document.getElementById('repoInput')?.focus();
      });
    }

    if (btnToggleSidebar && sidebar) {
      btnToggleSidebar.addEventListener('click', () => {
        sidebar.classList.toggle('mobile-open');
      });
    }
  }

  // --- Comprobación de Salud de la API (/health) ---
  async function checkSystemHealth() {
    const indicator = document.getElementById('systemStatusText');
    const pulseDot = document.getElementById('pulseDot');
    const startTime = performance.now();

    try {
      const res = await fetch('/health');
      const latency = Math.round(performance.now() - startTime);
      state.systemHealth.latencyMs = latency;

      if (res.ok) {
        state.systemHealth.status = 'online';
        if (indicator) indicator.textContent = `API Operativa (${latency} ms)`;
        if (pulseDot) pulseDot.style.backgroundColor = 'var(--color-pass)';
      } else {
        state.systemHealth.status = 'degraded';
        if (indicator) indicator.textContent = 'API Degradada';
        if (pulseDot) pulseDot.style.backgroundColor = 'var(--color-unknown)';
      }
    } catch {
      state.systemHealth.status = 'offline';
      if (indicator) indicator.textContent = 'Sin Conexión';
      if (pulseDot) pulseDot.style.backgroundColor = 'var(--color-fail)';
    }

    updateAdminHealthCard();
  }

  // --- Lógica del Evaluador de Controles (Core) ---
  function initEvaluator() {
    const form = document.getElementById('evaluatorForm');
    const repoInput = document.getElementById('repoInput');
    const branchInput = document.getElementById('branchInput');
    const chips = document.querySelectorAll('.chip-btn');
    const btnCancel = document.getElementById('btnCancelEval');
    if (!form) return;

    renderControlSelector();
    loadControlCatalog();

    // Chips de ejemplo rápido
    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        const repoVal = chip.dataset.repo;
        const branchVal = chip.dataset.branch || 'main';
        if (repoInput) repoInput.value = repoVal;
        if (branchInput) branchInput.value = branchVal;
      });
    });

    // Envío del formulario
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const rawRepo = repoInput.value.trim();
      const branch = branchInput ? branchInput.value.trim() : 'main';

      const normalizedRepository = normalizeGithubRepository(rawRepo);
      if (!normalizedRepository) {
        setEvaluatorFeedback('Ingresa un repositorio válido. Ejemplo: Medalcode/SecureCode o https://github.com/Medalcode/SecureCode', 'error');
        repoInput.focus();
        return;
      }

      const { owner, repository, canonical } = normalizedRepository;
      repoInput.value = canonical;

      const selectedRule = getSelectedRule();
      if (selectedRule?.branch_required && !branch) {
        setEvaluatorFeedback('Indica la rama que deseas auditar para este control.', 'error');
        branchInput?.focus();
        return;
      }

      state.evaluationAbortController = new AbortController();
      setEvaluationBusy(true);

      try {
        await executeEvaluation(state.selectedControl, owner, repository, branch, state.evaluationAbortController.signal);
        setEvaluatorFeedback('Evaluación finalizada. La evidencia se guardó de forma inmutable.', 'success');
      } catch (err) {
        if (err.name === 'AbortError') {
          setEvaluatorFeedback('La evaluación fue cancelada antes de finalizar. No se registró ningún resultado.', 'neutral');
        } else {
          renderErrorResult(err.message);
        }
      } finally {
        state.evaluationAbortController = null;
        setEvaluationBusy(false);
      }
    });

    btnCancel?.addEventListener('click', () => state.evaluationAbortController?.abort());

    // Botón de copia de Hash
    const btnCopyHash = document.getElementById('btnCopyHash');
    if (btnCopyHash) {
      btnCopyHash.addEventListener('click', () => {
        const hashText = document.getElementById('resultHashText').textContent;
        navigator.clipboard.writeText(hashText).then(() => {
          btnCopyHash.textContent = '¡Copiado!';
          setTimeout(() => { btnCopyHash.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copiar'; }, 2000);
        });
      });
    }

    document.getElementById('btnCopyVerificationLink')?.addEventListener('click', () => {
      const evaluationId = document.getElementById('resEvaluationId')?.textContent;
      if (!evaluationId || evaluationId === 'Sin persistencia') return;
      const verifyUrl = `${window.location.origin}/api/v1/verify/${encodeURIComponent(evaluationId)}`;
      navigator.clipboard.writeText(verifyUrl).then(() => {
        const button = document.getElementById('btnCopyVerificationLink');
        button.textContent = 'Enlace copiado';
        setTimeout(() => { button.textContent = 'Verificar'; }, 2000);
      });
    });

    // Botón de nueva evaluación desde tarjeta de resultados
    const btnResetResult = document.getElementById('btnResetResult');
    if (btnResetResult) {
      btnResetResult.addEventListener('click', () => {
        document.getElementById('resultContainer').classList.remove('active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
  }

  function getSelectedRule() {
    return state.rules.find(rule => rule.control_id === state.selectedControl) || state.rules[0];
  }

  function renderControlSelector() {
    const selector = document.getElementById('controlSelector');
    if (!selector) return;
    selector.innerHTML = state.rules.map(rule => `
      <button type="button" class="control-btn ${rule.control_id === state.selectedControl ? 'active' : ''}" data-control="${escapeHTML(rule.control_id)}" role="radio" aria-checked="${rule.control_id === state.selectedControl}">
        <span class="control-code">Control Canónico ${escapeHTML(rule.control_id)}</span>
        <span>${escapeHTML(rule.name)}</span>
        <span class="control-description">${escapeHTML(rule.short_description || rule.description)}</span>
      </button>`).join('');
    selector.querySelectorAll('.control-btn').forEach(button => {
      button.addEventListener('click', () => selectControl(button.dataset.control));
    });
    selectControl(state.selectedControl, false);
  }

  function selectControl(controlId, focus = true) {
    const rule = state.rules.find(item => item.control_id === controlId) || state.rules[0];
    if (!rule) return;
    state.selectedControl = rule.control_id;
    document.querySelectorAll('.control-btn').forEach(button => {
      const active = button.dataset.control === rule.control_id;
      button.classList.toggle('active', active);
      button.setAttribute('aria-checked', String(active));
      if (active && focus) button.focus();
    });
    const branchGroup = document.getElementById('branchInputGroup');
    const branchInput = document.getElementById('branchInput');
    if (branchGroup) branchGroup.hidden = !rule.branch_required;
    if (branchInput) branchInput.required = Boolean(rule.branch_required);
    const help = document.getElementById('evaluatorControlHelp');
    if (help) help.textContent = rule.description;
  }

  async function loadControlCatalog() {
    try {
      const res = await fetch('/api/v1/rules', { headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error('No disponible');
      const catalog = await res.json();
      const deployedIds = new Set((catalog.rules || []).map(rule => rule.control_id || rule.id));
      const deployedRules = state.rules.filter(rule => deployedIds.has(rule.control_id));
      if (deployedRules.length) state.rules = deployedRules;
      const count = Number.isInteger(catalog.active_controls) ? catalog.active_controls : state.rules.length;
      const countElement = document.getElementById('activeControlsCount');
      if (countElement) countElement.textContent = String(count).padStart(2, '0');
      renderControlSelector();
    } catch {
      // The preloaded catalog remains usable if the public catalog endpoint is temporarily unavailable.
      setEvaluatorFeedback('Catálogo local disponible; no fue posible confirmar la versión desplegada.', 'neutral');
    }
  }

  function setEvaluatorFeedback(message = '', tone = 'neutral') {
    const feedback = document.getElementById('evaluatorFeedback');
    if (!feedback) return;
    feedback.textContent = message;
    feedback.dataset.tone = tone;
  }

  function setEvaluationBusy(isBusy) {
    const button = document.getElementById('btnSubmitEval');
    const cancel = document.getElementById('btnCancelEval');
    const form = document.getElementById('evaluatorForm');
    if (button) {
      button.disabled = isBusy;
      button.innerHTML = isBusy ? `
        <svg class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle><path d="M12 2a10 10 0 0 1 10 10"></path></svg>
        <span>Evaluando evidencia...</span>` : `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
        <span>Ejecutar Evaluación Determinista</span>`;
    }
    if (cancel) cancel.hidden = !isBusy;
    if (form) form.setAttribute('aria-busy', String(isBusy));
    if (isBusy) setEvaluatorFeedback('Consultando evidencia de GitHub. Puedes cancelar mientras la solicitud sigue en curso.', 'neutral');
  }

  function normalizeGithubRepository(input) {
    const value = String(input || '').trim().replace(/\/$/, '').replace(/\.git$/i, '');
    if (!value) return null;

    let path = value;
    if (/^https?:\/\//i.test(value)) {
      let parsed;
      try {
        parsed = new URL(value);
      } catch {
        return null;
      }
      if (parsed.protocol !== 'https:' || parsed.hostname.toLowerCase() !== 'github.com') return null;
      path = parsed.pathname.replace(/^\/+|\/+$/g, '');
    } else if (/^github\.com\//i.test(value)) {
      path = value.replace(/^github\.com\//i, '');
    }

    const parts = path.split('/').filter(Boolean);
    if (parts.length !== 2) return null;
    const [owner, repository] = parts;
    const githubName = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$/;
    if (!githubName.test(owner) || !githubName.test(repository)) return null;
    return { owner, repository, canonical: `${owner}/${repository}` };
  }

  // --- Ejecución de la Petición al Backend ---
  async function executeEvaluation(controlId, owner, repo, branch, signal) {
    const needsBranch = getSelectedRule()?.branch_required === true;
    const endpoint = `/api/v1/evaluations/${controlId.toLowerCase()}`;
    const payload = needsBranch
      ? { owner, repository: repo, branch: branch || 'main' }
      : { owner, repository: repo };

    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };

    if (state.token) {
      headers['Authorization'] = `Bearer ${state.token}`;
    }

    const res = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal
    });

    if (res.status === 401) {
      openAuthModal();
      throw new Error('401 No autorizado: inicie sesión con credenciales válidas.');
    }

    if (res.status === 502) {
      renderServiceUnavailable('Falla de infraestructura o comunicación ascendente con la API de GitHub (HTTP 502). No se registró evaluación parcial.');
      throw new Error('No fue posible consultar GitHub. Reintenta en unos minutos.');
    }

    if (res.status === 422) {
      throw new Error(await getApiError(res, 'Los datos del repositorio o la rama no cumplen el formato válido de GitHub.'));
    }

    if (!res.ok) {
      throw new Error(`Error en el servidor: HTTP ${res.status}`);
    }

    const data = await res.json();
    renderEvaluationResult(data);
    addHistoryEntry(data);
    incrementUsedQuota();
  }

  // --- Renderizado del Resultado Triestado (PASS / FAIL / UNKNOWN) ---
  function renderEvaluationResult(data) {
    const container = document.getElementById('resultContainer');
    const banner = document.getElementById('resultBanner');
    const bannerIcon = document.getElementById('resultBannerIcon');
    const bannerTitle = document.getElementById('resultBannerTitle');
    const bannerBadge = document.getElementById('resultBannerBadge');

    const status = data.status; // 'PASS', 'FAIL', 'UNKNOWN'

    banner.className = `result-banner ${status.toLowerCase()}`;

    if (status === 'PASS') {
      bannerIcon.textContent = '✓';
      bannerTitle.textContent = 'PASS — Control Conforme';
      bannerBadge.textContent = 'CONFORME';
      renderAction('Sin acción correctiva requerida. La configuración actual satisface todos los criterios de la regla canónica.');
    } else if (status === 'FAIL') {
      bannerIcon.textContent = '✗';
      bannerTitle.textContent = 'FAIL — Control No Conforme';
      bannerBadge.textContent = 'NO CONFORME';
      renderAction('Ajuste la configuración de protección en el repositorio de GitHub y vuelva a evaluar para cumplir la política.');
    } else {
      bannerIcon.textContent = '?';
      bannerTitle.textContent = 'UNKNOWN — Evidencia Insuficiente';
      bannerBadge.textContent = 'DESCONOCIDO';
      renderAction('La evidencia técnica no está disponible o es ambigua (permisos insuficientes o rama no observable). No interpretarlo como incumplimiento.');
    }

    // Detalles generales
    document.getElementById('resControlId').textContent = data.control_id;
    document.getElementById('resRuleVersion').textContent = data.rule
      ? `${data.rule.id} · v${data.rule.version}`
      : 'Regla no informada';
    document.getElementById('resRepository').textContent = `${data.source.repository} (${data.source.branch})`;
    document.getElementById('resEvaluatedAt').textContent = new Date(data.evaluated_at).toLocaleString();
    document.getElementById('resEvaluationId').textContent = data.evaluation_id;
    document.getElementById('resultHashText').textContent = data.evidence.hash;
    renderVerificationBreakdown(data);

    // JSON Payload
    document.getElementById('jsonPayloadBody').textContent = JSON.stringify(data, null, 2);

    container.classList.add('active');
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function renderAction(text) {
    const actionEl = document.getElementById('resultActionText');
    if (actionEl) actionEl.textContent = text;
  }

  function renderVerificationBreakdown(data) {
    const summary = document.getElementById('verificationSummary');
    const checks = document.getElementById('verificationChecks');
    const source = document.getElementById('verificationSource');
    if (!summary || !checks || !source) return;

    const evidence = data.evidence || {};
    const isGH001 = data.control_id === 'GH-001';
    const isGH003 = data.control_id === 'GH-003';
    const asBoolean = (value) => value === true ? 'Sí' : value === false ? 'No' : 'No disponible';
    const resultLabel = data.status === 'PASS' ? 'Cumple' : data.status === 'FAIL' ? 'No cumple' : 'No verificable';
    const checkRow = (label, expected, observed, passed) => `
      <div class="verification-check ${passed === true ? 'pass' : passed === false ? 'fail' : 'unknown'}">
        <span class="verification-check-icon">${passed === true ? '✓' : passed === false ? '!' : '?'}</span>
        <div>
          <span class="verification-check-label">${escapeHTML(label)}</span>
          <span class="verification-check-detail"><b>Política:</b> ${escapeHTML(expected)} <span aria-hidden="true">·</span> <b>Encontrado:</b> ${escapeHTML(observed)}</span>
        </div>
      </div>`;

    source.textContent = `Fuente: ${data.source?.type || 'GitHub'} · evidencia consultada ${new Date(data.collected_at).toLocaleString()}`;

    if (isGH001) {
      const approvals = evidence.required_review_approvals;
      const stale = evidence.dismiss_stale_reviews;
      summary.textContent = `${resultLabel}: se contrastó la política de revisiones de la rama ${data.source.branch}.`;
      checks.innerHTML = [
        checkRow('Aprobaciones requeridas', 'al menos 2', approvals ?? 'No disponible', typeof approvals === 'number' ? approvals >= 2 : null),
        checkRow('Revisiones obsoletas', 'se descartan al incorporar cambios nuevos', asBoolean(stale), typeof stale === 'boolean' ? stale === true : null)
      ].join('');
    } else if (isGH003) {
      const signatures = evidence.required_signatures_enabled;
      const branch = evidence.branch || data.source.branch || 'No disponible';
      summary.textContent = `${resultLabel}: se verificó que GitHub exija commits firmados en la rama auditada.`;
      checks.innerHTML = [
        checkRow('Rama auditada', 'una rama observable', branch, Boolean(evidence.branch)),
        checkRow('Firmas de commits exigidas', 'activas', asBoolean(signatures), typeof signatures === 'boolean' ? signatures === true : null)
      ].join('');
    } else {
      const protectedBranch = evidence.protection_enabled;
      const defaultBranch = evidence.default_branch || data.source.branch || 'No disponible';
      summary.textContent = `${resultLabel}: se verificó que la rama predeterminada del repositorio tenga una protección activa.`;
      checks.innerHTML = [
        checkRow('Rama predeterminada detectada', 'una rama observable', defaultBranch, Boolean(evidence.default_branch)),
        checkRow('Protección de rama', 'activa', asBoolean(protectedBranch), typeof protectedBranch === 'boolean' ? protectedBranch === true : null)
      ].join('');
    }
  }

  function renderServiceUnavailable(message) {
    const container = document.getElementById('resultContainer');
    const banner = document.getElementById('resultBanner');
    const bannerIcon = document.getElementById('resultBannerIcon');
    const bannerTitle = document.getElementById('resultBannerTitle');
    const bannerBadge = document.getElementById('resultBannerBadge');

    banner.className = 'result-banner error';
    bannerIcon.textContent = '!';
    bannerTitle.textContent = '502 — Servicio No Disponible';
    bannerBadge.textContent = 'ERROR INFRAESTRUCTURA';
    renderAction(message);

    document.getElementById('resControlId').textContent = 'N/A';
    document.getElementById('resRepository').textContent = 'Falla de conexión aguas arriba';
    document.getElementById('resEvaluatedAt').textContent = new Date().toLocaleString();
    document.getElementById('resEvaluationId').textContent = 'Sin persistencia';
    document.getElementById('resultHashText').textContent = '0000000000000000000000000000000000000000000000000000000000000000';
    document.getElementById('jsonPayloadBody').textContent = JSON.stringify({ error: message, code: 502 }, null, 2);

    container.classList.add('active');
    container.scrollIntoView({ behavior: 'smooth' });
  }

  function renderErrorResult(msg) {
    setEvaluatorFeedback(`No se pudo procesar la evaluación: ${msg}`, 'error');
  }

  // --- Historial Local de Evaluaciones (Estilo Chat sidebar) ---
  function initHistory() {
    renderHistoryList();
    loadPersistentHistory();
    document.getElementById('btnExportHistory')?.addEventListener('click', exportHistoryCSV);
  }

  function addHistoryEntry(data) {
    const entry = {
      id: data.evaluation_id,
      control: data.control_id,
      repo: `${data.source.repository}@${data.source.branch}`,
      status: data.status.toLowerCase(),
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      data: data
    };
    state.evalHistory.unshift(entry);
    if (state.evalHistory.length > 20) state.evalHistory.pop();
    localStorage.setItem('securecode_history', JSON.stringify(state.evalHistory));
    renderHistoryList();
    loadPersistentHistory();
  }

  async function loadPersistentHistory() {
    if (!state.token) return;
    try {
      const res = await fetch('/api/v1/evaluations/history?limit=20', {
        headers: { 'Authorization': `Bearer ${state.token}` }
      });
      if (!res.ok) return;
      const { evaluations } = await res.json();
      state.evalHistory = evaluations.map(item => ({
        id: item.evaluation_id,
        control: item.control_id,
        repo: `${item.repository}@${item.branch}`,
        status: item.status.toLowerCase(),
        time: new Date(item.evaluated_at).toLocaleString(),
        data: null
      }));
      renderHistoryList();
    } catch { /* La UI conserva el historial local si la red no está disponible. */ }
  }

  async function loadHistoricalEvaluation(record) {
    if (!record || !state.token) return;
    openEvaluatorForHistory();
    renderHistoricalLoading(record);
    try {
      const res = await fetch(`/api/v1/evaluations/${encodeURIComponent(record.id)}`, {
        headers: { 'Authorization': `Bearer ${state.token}` }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      record.data = await res.json();
      renderEvaluationResult(record.data);
    } catch {
      renderHistoricalLoadFailure();
    }
  }

  function renderHistoricalLoading(record) {
    const container = document.getElementById('resultContainer');
    const banner = document.getElementById('resultBanner');
    if (!container || !banner) return;
    banner.className = 'result-banner unknown';
    document.getElementById('resultBannerIcon').textContent = '…';
    document.getElementById('resultBannerTitle').textContent = 'Cargando auditoría anterior';
    document.getElementById('resultBannerBadge').textContent = record.control;
    renderAction('Recuperando la evidencia inmutable almacenada para esta evaluación.');
    container.classList.add('active');
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function renderHistoricalLoadFailure() {
    const banner = document.getElementById('resultBanner');
    if (!banner) return;
    banner.className = 'result-banner error';
    document.getElementById('resultBannerIcon').textContent = '!';
    document.getElementById('resultBannerTitle').textContent = 'No se pudo abrir la auditoría';
    document.getElementById('resultBannerBadge').textContent = 'REINTENTAR';
    renderAction('Actualiza la página e inicia sesión nuevamente. Si persiste, la evaluación puede no estar disponible para tu cuenta.');
  }

  function openEvaluatorForHistory() {
    // History is global. Always reveal the evaluator before rendering its detail.
    document.querySelector('.nav-item[data-view="evaluator"]')?.click();
  }

  function escapeHTML(value) {
    const node = document.createElement('span');
    node.textContent = String(value ?? '');
    return node.innerHTML;
  }

  function csvCell(value) {
    const text = String(value ?? '');
    // Prevent spreadsheet applications from interpreting exported audit data as formulas.
    const safe = /^[=+\-@]/.test(text) ? `'${text}` : text;
    return `"${safe.replaceAll('"', '""')}"`;
  }

  function exportHistoryCSV() {
    if (state.evalHistory.length === 0) {
      alert('No hay evaluaciones para exportar.');
      return;
    }
    const header = ['evaluation_id', 'control_id', 'repository_branch', 'status', 'evaluated_at'];
    const rows = state.evalHistory.map(item => [item.id, item.control, item.repo, item.status.toUpperCase(), item.time]);
    const csv = [header, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `securecode-audit-history-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function renderHistoryList() {
    const list = document.getElementById('historyList');
    if (!list) return;

    if (state.evalHistory.length === 0) {
      list.innerHTML = `<div style="padding: 12px; font-size: 11px; color: var(--text-faint); text-align: center;">Sin evaluaciones previas</div>`;
      return;
    }

    list.innerHTML = state.evalHistory.map((item, idx) => `
      <div class="history-item" data-idx="${idx}">
        <div style="display:flex; align-items:center; gap:8px; overflow:hidden;">
          <span class="status-dot ${item.status}"></span>
          <span style="font-weight:600;">${escapeHTML(item.control)}</span>
          <span style="text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">${escapeHTML(item.repo)}</span>
        </div>
        <span style="font-size:10px; color:var(--text-faint);">${item.time}</span>
      </div>
    `).join('');

    list.querySelectorAll('.history-item').forEach(el => {
      el.addEventListener('click', () => {
        const idx = el.dataset.idx;
        const record = state.evalHistory[idx];
        if (record && record.data) {
          openEvaluatorForHistory();
          renderEvaluationResult(record.data);
          document.querySelectorAll('.history-item').forEach(h => h.classList.remove('active'));
          el.classList.add('active');
        } else if (record) {
          loadHistoricalEvaluation(record);
          document.querySelectorAll('.history-item').forEach(h => h.classList.remove('active'));
          el.classList.add('active');
        }
      });
    });
  }

  // --- FinOps y Cuota de Consumo ---
  function initDashboard() {
    initFinOpsControls();
  }

  function initFinOpsControls() {
    const saveBudget = document.getElementById('btnSaveBudget');
    const budgetInput = document.getElementById('budgetLimitInput');
    const alertSelect = document.getElementById('budgetAlertSelect');
    saveBudget?.addEventListener('click', () => {
      const budget = Number(budgetInput?.value);
      if (!Number.isFinite(budget) || budget < 10) { document.getElementById('budgetFeedback').textContent = 'Ingresa un presupuesto de al menos $10 CLP.'; return; }
      saveFinOpsSettings(budget, Number(alertSelect?.value || 80), Boolean(document.getElementById('budgetAlertEnabled')?.checked));
    });
  }

  function updateFinOpsAccess() {
    const panel = document.getElementById('finopsPanel');
    const notice = document.getElementById('finopsAccessNotice');
    const authenticated = Boolean(state.token && state.accessRole);
    if (panel) panel.hidden = !authenticated;
    if (notice) notice.hidden = authenticated;
  }

  async function loadFinOps() {
    updateFinOpsAccess();
    if (!state.token) return;
    try {
      const response = await fetch('/api/v1/finops', { headers: { 'Authorization': 'Bearer ' + state.token } });
      if (!response.ok) throw new Error('No se pudo cargar el consumo.');
      state.finops = await response.json();
      renderFinOps(state.finops);
    } catch (error) {
      const feedback = document.getElementById('budgetFeedback');
      if (feedback) feedback.textContent = error.message;
    }
  }

  async function saveFinOpsSettings(budget, threshold, enabled) {
    const feedback = document.getElementById('budgetFeedback');
    if (!state.token) return;
    if (feedback) feedback.textContent = 'Guardando preferencia…';
    try {
      const response = await fetch('/api/v1/finops', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + state.token },
        body: JSON.stringify({ budget_clp: budget, alert_threshold_pct: threshold, alert_enabled: enabled })
      });
      if (!response.ok) throw new Error(await getApiError(response, 'No se pudo guardar el control.'));
      state.finops = await response.json();
      renderFinOps(state.finops);
      if (feedback) feedback.textContent = 'Preferencia FinOps guardada. Requiere Cloud Billing para activar alertas de gasto reales.';
    } catch (error) {
      if (feedback) feedback.textContent = error.message;
    }
  }

  function renderFinOps(data) {
    document.getElementById('quotaUsedText').textContent = Number(data.evaluations_current_period).toLocaleString('es-CL');
    document.getElementById('quotaMaxText').textContent = Number(data.evaluations_all_time).toLocaleString('es-CL');
    document.getElementById('usageScopeLabel').textContent = data.scope === 'platform' ? 'Plataforma' : 'Cuenta';
    document.getElementById('usagePeriodStart').textContent = new Date(data.period_start).toLocaleDateString('es-CL');
    document.getElementById('quotaPctText').textContent = 'Evaluaciones del período actual';
    document.getElementById('quotaBarFill').style.width = data.evaluations_all_time ? Math.min(100, Math.round((data.evaluations_current_period / data.evaluations_all_time) * 100)) + '%' : '0%';
    document.getElementById('budgetLimitInput').value = String(data.budget_clp);
    document.getElementById('budgetAlertSelect').value = String(data.alert_threshold_pct);
    document.getElementById('budgetAlertEnabled').checked = Boolean(data.alert_enabled);
    document.getElementById('billingStatusBadge').textContent = 'SIN CONEXIÓN';
    document.getElementById('projectedChargeText').textContent = 'No disponible';
  }

  // --- Ciclo de suscripción persistido por cuenta ---
  function initSubscription() {
    document.getElementById('subscriptionConfirmCheckbox')?.addEventListener('change', event => {
      const confirm = document.getElementById('btnConfirmSubscriptionChange');
      if (confirm) confirm.disabled = !event.target.checked;
    });
    document.getElementById('btnCancelSubscriptionChange')?.addEventListener('click', clearSubscriptionConfirmation);
    document.getElementById('btnConfirmSubscriptionChange')?.addEventListener('click', confirmSubscriptionChange);
    updateSubscriptionAccess();
  }

  function updateSubscriptionAccess() {
    const panel = document.getElementById('subscriptionPanel');
    const notice = document.getElementById('subscriptionAccessNotice');
    const authenticated = Boolean(state.token && state.accessRole);
    if (panel) panel.hidden = !authenticated;
    if (notice) notice.hidden = authenticated;
  }

  async function loadSubscription() {
    updateSubscriptionAccess();
    if (!state.token) return;
    try {
      const headers = { 'Authorization': 'Bearer ' + state.token };
      const results = await Promise.all([
        fetch('/api/v1/subscription', { headers }),
        fetch('/api/v1/subscription/history?limit=20', { headers })
      ]);
      if (!results[0].ok) throw new Error('No se pudo cargar la suscripción.');
      state.subscriptionData = await results[0].json();
      renderSubscription(state.subscriptionData);
      renderSubscriptionHistory(results[1].ok ? await results[1].json() : []);
    } catch (error) {
      const status = document.getElementById('planSaveStatus');
      if (status) status.textContent = error.message;
    }
  }

  function formatSubscriptionDate(value) {
    return new Date(value).toLocaleDateString('es-CL', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  function planLabel(id) {
    return id === 'premium' ? 'Premium' : id === 'pro' ? 'Pro' : '—';
  }

  function renderSubscription(subscription) {
    const activePlan = subscription.catalog.find(plan => plan.id === subscription.plan_id);
    if (!activePlan) return;
    document.getElementById('activePlanName').textContent = activePlan.name;
    document.getElementById('subscriptionPeriodText').textContent = 'Vigente desde ' + formatSubscriptionDate(subscription.started_at) + ' hasta ' + formatSubscriptionDate(subscription.expires_at);
    document.getElementById('activePlanFeatures').innerHTML = activePlan.features.map(feature => '<li>✓ ' + escapeHTML(feature) + '</li>').join('');
    document.getElementById('billingModeBadge').textContent = 'DEMO · SIN COBRO';
    const changeStatus = document.getElementById('subscriptionChangeStatus');
    const changeHelp = document.getElementById('subscriptionChangeHelp');
    const planStatus = document.getElementById('planSaveStatus');
    if (subscription.can_change) {
      changeStatus.textContent = 'Cambio disponible';
      changeHelp.textContent = 'Puedes confirmar un cambio de plan para iniciar un nuevo período de 30 días.';
      planStatus.textContent = 'Cambio de plan disponible';
    } else {
      changeStatus.textContent = 'Período bloqueado';
      changeHelp.textContent = 'Próximo cambio disponible: ' + formatSubscriptionDate(subscription.next_change_at) + '.';
      planStatus.textContent = 'Un cambio por cada período de 30 días';
    }
    const options = document.getElementById('planOptions');
    const details = document.getElementById('planDetails');
    options.innerHTML = subscription.catalog.map(plan => {
      const active = plan.id === subscription.plan_id;
      const disabled = active || !subscription.can_change;
      const stateLabel = active ? 'Plan activo' : subscription.can_change ? 'Disponible para cambio' : 'Disponible al finalizar el período';
      return '<button type="button" class="plan-option ' + (active ? 'active' : '') + '" data-plan-id="' + escapeHTML(plan.id) + '" ' + (disabled ? 'disabled' : '') + '><b>' + escapeHTML(plan.name) + '</b><span>$' + Number(plan.price_clp).toLocaleString('es-CL') + ' CLP/mes</span><small>' + stateLabel + '</small></button>';
    }).join('');
    options.querySelectorAll('[data-plan-id]').forEach(button => button.addEventListener('click', () => prepareSubscriptionConfirmation(button.dataset.planId)));
    details.innerHTML = '<div><b>' + escapeHTML(activePlan.name) + '</b><span>$' + Number(activePlan.price_clp).toLocaleString('es-CL') + ' CLP/mes · proyección ES2</span></div><ul>' + activePlan.features.map(feature => '<li>✓ ' + escapeHTML(feature) + '</li>').join('') + '</ul>';
  }

  function prepareSubscriptionConfirmation(planId) {
    const subscription = state.subscriptionData;
    const selected = subscription?.catalog.find(plan => plan.id === planId);
    if (!subscription || !selected || !subscription.can_change) return;
    state.pendingSubscriptionPlan = planId;
    document.getElementById('subscriptionConfirmTitle').textContent = 'Confirmar plan ' + selected.name;
    document.getElementById('subscriptionConfirmDescription').textContent = 'El plan ' + selected.name + ' quedará vigente por 30 días desde la confirmación. El cambio se registrará en tu historial.';
    document.getElementById('subscriptionConfirmCheckbox').checked = false;
    document.getElementById('btnConfirmSubscriptionChange').disabled = true;
    document.getElementById('subscriptionConfirmPanel').hidden = false;
  }

  function clearSubscriptionConfirmation() {
    state.pendingSubscriptionPlan = null;
    const panel = document.getElementById('subscriptionConfirmPanel');
    if (panel) panel.hidden = true;
  }

  async function confirmSubscriptionChange() {
    if (!state.pendingSubscriptionPlan) return;
    const status = document.getElementById('planSaveStatus');
    try {
      const response = await fetch('/api/v1/subscription', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + state.token },
        body: JSON.stringify({ plan_id: state.pendingSubscriptionPlan, confirmation: true })
      });
      if (!response.ok) throw new Error(await getApiError(response, 'No se pudo cambiar el plan.'));
      clearSubscriptionConfirmation();
      state.subscriptionData = await response.json();
      renderSubscription(state.subscriptionData);
      await loadSubscription();
      if (status) status.textContent = 'Cambio confirmado y registrado.';
    } catch (error) {
      if (status) status.textContent = error.message;
    }
  }

  function renderSubscriptionHistory(events) {
    const body = document.getElementById('subscriptionHistoryBody');
    if (!body) return;
    body.innerHTML = events.map(event => '<tr><td>' + formatSubscriptionDate(event.occurred_at) + '</td><td>' + (event.event_type === 'initialized' ? 'Suscripción inicializada' : 'Cambio confirmado') + '</td><td>' + planLabel(event.previous_plan_id) + '</td><td>' + planLabel(event.new_plan_id) + '</td><td>' + formatSubscriptionDate(event.effective_from) + ' — ' + formatSubscriptionDate(event.effective_until) + '</td></tr>').join('') || '<tr><td colspan="5">Aún no hay cambios confirmados.</td></tr>';
  }

  function incrementUsedQuota() {
    loadFinOps();
  }

  function updateQuotaUI() {
    if (state.finops) renderFinOps(state.finops);
  }

  // --- Consola de Administración ---
  function initAdminConsole() {
    const btnSimulate = document.getElementById('btnSimulateAudit');
    const createUserForm = document.getElementById('createUserForm');
    const btnRefreshUsers = document.getElementById('btnRefreshUsers');
    if (btnSimulate) {
      btnSimulate.addEventListener('click', () => {
        const dummy = {
          evaluation_id: 'sim-' + Math.random().toString(36).substring(2, 9),
          control_id: 'GH-001',
          rule: { id: 'GH-001-RULE', version: 1 },
          status: 'PASS',
          source: { type: 'GitHub', repository: 'Medalcode/SecureCode', branch: 'main' },
          evidence: {
            required_review_approvals: 2,
            dismiss_stale_reviews: true,
            hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
          },
          collected_at: new Date().toISOString(),
          evaluated_at: new Date().toISOString()
        };
        renderEvaluationResult(dummy);
        addHistoryEntry(dummy);
        alert('Simulación determinista ejecutada exitosamente.');
      });
    }
    if (btnRefreshUsers) btnRefreshUsers.addEventListener('click', refreshAdminUsers);
    if (createUserForm) createUserForm.addEventListener('submit', createManagedUser);
    document.getElementById('passwordResetForm')?.addEventListener('submit', submitPasswordReset);
    document.getElementById('btnCancelPasswordReset')?.addEventListener('click', closePasswordResetModal);
    document.getElementById('newUserPassword')?.addEventListener('input', () => updatePasswordFormState('newUserPassword', 'newUserPasswordConfirm', 'newUserPasswordPolicy', 'newUserPasswordMatch'));
    document.getElementById('newUserPasswordConfirm')?.addEventListener('input', () => updatePasswordFormState('newUserPassword', 'newUserPasswordConfirm', 'newUserPasswordPolicy', 'newUserPasswordMatch'));
    document.getElementById('resetUserPassword')?.addEventListener('input', () => updatePasswordFormState('resetUserPassword', 'resetUserPasswordConfirm', 'resetUserPasswordPolicy', 'resetUserPasswordMatch'));
    document.getElementById('resetUserPasswordConfirm')?.addEventListener('input', () => updatePasswordFormState('resetUserPassword', 'resetUserPasswordConfirm', 'resetUserPasswordPolicy', 'resetUserPasswordMatch'));
    document.getElementById('newUserRole')?.addEventListener('change', updateAdminRoleAcknowledgement);
    document.querySelectorAll('[data-password-toggle]').forEach(button => button.addEventListener('click', () => togglePasswordVisibility(button)));
    ['adminUserSearch', 'adminRoleFilter', 'adminStatusFilter'].forEach(id => {
      document.getElementById(id)?.addEventListener('input', renderAdminUsers);
      document.getElementById(id)?.addEventListener('change', renderAdminUsers);
    });
  }

  async function refreshAdminUsers() {
    const management = document.getElementById('adminUserManagement');
    const notice = document.getElementById('adminAccessNotice');
    const body = document.getElementById('adminUsersBody');
    if (!management || !notice || !body) return;
    if (!state.token || state.accessRole !== 'admin') {
      management.hidden = true;
      document.getElementById('adminAuditTrail').hidden = true;
      notice.hidden = false;
      return;
    }
    try {
      const res = await fetch('/api/v1/admin/users', { headers: { 'Authorization': `Bearer ${state.token}` } });
      if (!res.ok) throw new Error('No autorizado');
      state.adminUsers = await res.json();
      renderAdminUsers();
      refreshUserAuditEvents();
      management.hidden = false;
      notice.hidden = true;
    } catch {
      management.hidden = true;
      document.getElementById('adminAuditTrail').hidden = true;
      notice.hidden = false;
      notice.textContent = 'No fue posible cargar la administración de usuarios.';
    }
  }

  function renderAdminUsers() {
    const body = document.getElementById('adminUsersBody');
    if (!body) return;
    const search = (document.getElementById('adminUserSearch')?.value || '').trim().toLowerCase();
    const role = document.getElementById('adminRoleFilter')?.value || '';
    const status = document.getElementById('adminStatusFilter')?.value || '';
    const users = state.adminUsers.filter(user =>
      (!search || user.username.toLowerCase().includes(search)) &&
      (!role || user.role === role) &&
      (!status || (status === 'active') === Boolean(user.active))
    );
    const count = document.getElementById('adminUserCount');
    if (count) count.textContent = `${users.length} de ${state.adminUsers.length} cuentas`;
    const activeUsers = state.adminUsers.filter(user => user.active).length;
    const administrators = state.adminUsers.filter(user => user.role === 'admin' && user.active).length;
    document.getElementById('adminTotalUsers').textContent = String(state.adminUsers.length);
    document.getElementById('adminActiveUsers').textContent = String(activeUsers);
    document.getElementById('adminAdminUsers').textContent = String(administrators);
    body.innerHTML = users.map(user => {
        const action = user.username === state.user.username
          ? '<span class="admin-helper">Cuenta actual</span>'
          : `<div class="admin-action-group"><button class="btn-inline-danger" data-action="active" data-user-id="${escapeHTML(user.id)}" data-active="${user.active}">${user.active ? 'Desactivar' : 'Activar'}</button><button class="btn-copy" data-action="role" data-user-id="${escapeHTML(user.id)}" data-role="${user.role}">${user.role === 'admin' ? 'Hacer auditor' : 'Hacer admin'}</button><button class="btn-copy" data-action="password" data-user-id="${escapeHTML(user.id)}">Restablecer</button></div>`;
        const activity = user.last_login_at || user.updated_at || user.created_at;
        return `<tr><td>${escapeHTML(user.username)}</td><td>${user.role === 'admin' ? 'Administrador' : 'Auditor'}</td><td>${user.active ? 'Activo' : 'Desactivado'}</td><td>${activity ? new Date(activity).toLocaleString() : 'Sin registros'}</td><td>${action}</td></tr>`;
      }).join('') || '<tr><td colspan="5">No hay cuentas que coincidan con los filtros.</td></tr>';
    body.querySelectorAll('[data-user-id]').forEach(button => button.addEventListener('click', () => manageUserAction(button)));
  }

  async function refreshUserAuditEvents() {
    const trail = document.getElementById('adminAuditTrail');
    const body = document.getElementById('adminAuditBody');
    if (!trail || !body || !state.token || state.accessRole !== 'admin') return;
    try {
      const res = await fetch('/api/v1/admin/user-audit-events?limit=25', { headers: { 'Authorization': `Bearer ${state.token}` } });
      if (!res.ok) throw new Error('No autorizado');
      const events = await res.json();
      const actionLabel = { account_created: 'Cuenta creada', account_updated: 'Cuenta actualizada' };
      body.innerHTML = events.map(event => `<tr><td>${new Date(event.created_at).toLocaleString()}</td><td>${actionLabel[event.action] || escapeHTML(event.action)}</td><td>${escapeHTML(event.actor_username || 'Sistema')}</td><td>${escapeHTML(event.target_username || '—')}</td><td>${escapeHTML(formatAuditDetails(event.details))}</td></tr>`).join('') || '<tr><td colspan="5">Aún no hay eventos administrativos.</td></tr>';
      trail.hidden = false;
    } catch {
      trail.hidden = true;
    }
  }

  function formatAuditDetails(details) {
    if (!details || typeof details !== 'object') return '—';
    if (details.password_reset) return 'Contraseña restablecida';
    return Object.entries(details).map(([key, value]) => `${key}: ${typeof value === 'object' ? `${value.from} → ${value.to}` : value}`).join(' · ') || '—';
  }

  async function createManagedUser(event) {
    event.preventDefault();
    const feedback = document.getElementById('adminUserFeedback');
    const button = document.getElementById('btnCreateUser');
    const payload = {
      username: document.getElementById('newUsername').value.trim(),
      password: document.getElementById('newUserPassword').value,
      role: document.getElementById('newUserRole').value
    };
    if (!validatePasswordForm('newUserPassword', 'newUserPasswordConfirm', 'newUserPasswordPolicy', 'newUserPasswordMatch')) {
      setAdminFeedback('Revisa los requisitos y confirma la contraseña temporal.', 'error');
      return;
    }
    if (payload.role === 'admin' && !document.getElementById('newAdminAcknowledgementCheck').checked) {
      setAdminFeedback('Confirma explícitamente la asignación de privilegios administrativos.', 'error');
      return;
    }
    if (!document.getElementById('newUsername').checkValidity()) {
      setAdminFeedback('Ingresa un correo electrónico válido para la nueva cuenta.', 'error');
      document.getElementById('newUsername').focus();
      return;
    }
    if (button) button.disabled = true;
    setAdminFeedback('Creando cuenta y registrando la trazabilidad administrativa…');
    try {
      const res = await fetch('/api/v1/admin/users', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` }, body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(await getApiError(res, res.status === 409 ? 'El usuario ya existe.' : 'No se pudo crear el usuario.'));
      event.target.reset();
      updatePasswordFormState('newUserPassword', 'newUserPasswordConfirm', 'newUserPasswordPolicy', 'newUserPasswordMatch');
      updateAdminRoleAcknowledgement();
      setAdminFeedback('Cuenta creada correctamente. La contraseña temporal no se conserva en SecureCode.', 'success');
      await refreshAdminUsers();
    } catch (error) {
      setAdminFeedback(error.message, 'error');
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function manageUserAction(button) {
    const action = button.dataset.action;
    const username = button.closest('tr')?.querySelector('td')?.textContent || 'este usuario';
    if (action === 'active' && button.dataset.active === 'true' && !window.confirm(`¿Desactivar el acceso de ${username}? Podrás reactivarlo después.`)) return;
    if (action === 'role' && !window.confirm(`¿Cambiar el rol de ${username}? El nuevo permiso tendrá efecto en su próximo inicio de sesión.`)) return;
    const payload = action === 'active'
      ? { active: button.dataset.active !== 'true' }
      : action === 'role'
        ? { role: button.dataset.role === 'admin' ? 'auditor' : 'admin' }
        : null;
    if (action === 'password') {
      openPasswordResetModal(button.dataset.userId, username);
      return;
    }
    try {
      const res = await fetch(`/api/v1/admin/users/${encodeURIComponent(button.dataset.userId)}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(await getApiError(res, 'No se pudo actualizar el usuario.'));
      await refreshAdminUsers();
      setAdminFeedback(`Cuenta ${action === 'active' ? 'actualizada' : 'con rol actualizado'} correctamente.`, 'success');
    } catch (error) { setAdminFeedback(error.message, 'error'); }
  }

  function passwordRules(value) {
    return {
      length: value.length >= 12,
      lower: /[a-z]/.test(value),
      upper: /[A-Z]/.test(value),
      number: /\d/.test(value),
      symbol: /[^A-Za-z0-9]/.test(value)
    };
  }

  function updatePasswordFormState(passwordId, confirmationId, policyId, matchId) {
    const password = document.getElementById(passwordId)?.value || '';
    const confirmation = document.getElementById(confirmationId)?.value || '';
    const rules = passwordRules(password);
    document.getElementById(policyId)?.querySelectorAll('[data-rule]').forEach(item => {
      const valid = rules[item.dataset.rule];
      item.dataset.valid = String(valid);
      item.textContent = `${valid ? '✓' : '○'} ${item.textContent.replace(/^[✓○]\s*/, '')}`;
    });
    const match = document.getElementById(matchId);
    if (match) {
      match.textContent = !confirmation ? '' : password === confirmation ? 'Las contraseñas coinciden.' : 'Las contraseñas no coinciden.';
      match.dataset.tone = password === confirmation ? 'success' : 'error';
    }
  }

  function validatePasswordForm(passwordId, confirmationId, policyId, matchId) {
    updatePasswordFormState(passwordId, confirmationId, policyId, matchId);
    const password = document.getElementById(passwordId)?.value || '';
    const confirmation = document.getElementById(confirmationId)?.value || '';
    return Object.values(passwordRules(password)).every(Boolean) && password === confirmation;
  }

  function updateAdminRoleAcknowledgement() {
    const isAdmin = document.getElementById('newUserRole')?.value === 'admin';
    const acknowledgement = document.getElementById('newAdminAcknowledgement');
    const checkbox = document.getElementById('newAdminAcknowledgementCheck');
    if (acknowledgement) acknowledgement.hidden = !isAdmin;
    if (!isAdmin && checkbox) checkbox.checked = false;
  }

  function togglePasswordVisibility(button) {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;
    const visible = input.type === 'text';
    input.type = visible ? 'password' : 'text';
    button.textContent = visible ? 'Mostrar' : 'Ocultar';
    button.setAttribute('aria-label', visible ? 'Mostrar contraseña' : 'Ocultar contraseña');
  }

  function setAdminFeedback(message = '', tone = '') {
    const feedback = document.getElementById('adminUserFeedback');
    if (!feedback) return;
    feedback.textContent = message;
    feedback.dataset.tone = tone;
  }

  function openPasswordResetModal(userId, username) {
    state.passwordResetTarget = { userId, username };
    const modal = document.getElementById('passwordResetModal');
    document.getElementById('passwordResetDescription').textContent = `Define una nueva contraseña temporal para ${username}. No será mostrada nuevamente.`;
    document.getElementById('passwordResetForm').reset();
    document.getElementById('passwordResetFeedback').textContent = '';
    updatePasswordFormState('resetUserPassword', 'resetUserPasswordConfirm', 'resetUserPasswordPolicy', 'resetUserPasswordMatch');
    modal?.classList.add('active');
    modal?.setAttribute('aria-hidden', 'false');
    document.getElementById('resetUserPassword')?.focus();
  }

  function closePasswordResetModal() {
    const modal = document.getElementById('passwordResetModal');
    modal?.classList.remove('active');
    modal?.setAttribute('aria-hidden', 'true');
    state.passwordResetTarget = null;
  }

  async function submitPasswordReset(event) {
    event.preventDefault();
    const feedback = document.getElementById('passwordResetFeedback');
    const button = document.getElementById('btnConfirmPasswordReset');
    const target = state.passwordResetTarget;
    if (!target || !validatePasswordForm('resetUserPassword', 'resetUserPasswordConfirm', 'resetUserPasswordPolicy', 'resetUserPasswordMatch')) {
      if (feedback) feedback.textContent = 'Revisa los requisitos y confirma la contraseña.';
      return;
    }
    if (button) button.disabled = true;
    if (feedback) feedback.textContent = 'Restableciendo contraseña…';
    try {
      const res = await fetch(`/api/v1/admin/users/${encodeURIComponent(target.userId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` },
        body: JSON.stringify({ password: document.getElementById('resetUserPassword').value })
      });
      if (!res.ok) throw new Error(await getApiError(res, 'No se pudo restablecer la contraseña.'));
      closePasswordResetModal();
      setAdminFeedback(`Contraseña restablecida para ${target.username}.`, 'success');
      await refreshAdminUsers();
    } catch (error) {
      if (feedback) feedback.textContent = error.message;
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function getApiError(response, fallback) {
    try {
      const data = await response.json();
      return data.detail || fallback;
    } catch {
      return fallback;
    }
  }

  function updateAdminHealthCard() {
    const lat = document.getElementById('adminLatencyVal');
    const dbStat = document.getElementById('adminDbStatusVal');
    if (lat && state.systemHealth.latencyMs !== null) {
      lat.textContent = `${state.systemHealth.latencyMs} ms`;
    }
    if (dbStat) {
      dbStat.textContent = state.systemHealth.status === 'online' ? 'PostgreSQL 15 Conectado' : 'Desconectado';
    }
  }

  // --- Modal de Autenticación / Login ---
  function initAuthModal() {
    const modal = document.getElementById('authModal');
    const form = document.getElementById('loginForm');
    const btnClearSession = document.getElementById('btnClearSession');
    const btnCloseModal = document.getElementById('btnCloseAuthModal');
    const btnOpenLogin = document.getElementById('btnOpenLogin');

    if (btnOpenLogin) {
      btnOpenLogin.addEventListener('click', () => openAuthModal());
    }

    if (btnCloseModal) {
      btnCloseModal.addEventListener('click', () => closeAuthModal());
    }

    if (btnClearSession) {
      btnClearSession.addEventListener('click', () => {
        state.token = null;
        localStorage.removeItem('securecode_token');
        localStorage.removeItem('securecode_user');
        state.user.username = 'Sesión cerrada';
        state.accessRole = null;
        updateUserBadge();
        updateSettingsAccess();
        updateSubscriptionAccess();
        updateFinOpsAccess();
        refreshAdminUsers();
      });
    }

    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const user = document.getElementById('authUsername').value.trim();
        const pass = document.getElementById('authPassword').value;
        removeAuthAlert();

        const formData = new URLSearchParams();
        formData.append('username', user);
        formData.append('password', pass);

        try {
          const res = await fetch('/api/v1/auth/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
          });

          if (!res.ok) {
            showAuthError(res.status === 401
              ? 'Usuario o contraseña incorrectos. Verifique sus credenciales.'
              : 'No fue posible iniciar sesión. Inténtelo nuevamente.');
            return;
          }

          const data = await res.json();
          state.token = data.access_token;
          state.user.username = user;
          localStorage.setItem('securecode_token', state.token);
          localStorage.setItem('securecode_user', JSON.stringify(state.user));
          updateUserBadge();
          closeAuthModal();
          syncAuthenticatedUser();
        } catch (error) {
          showAuthError('Error al comunicarse con el servicio de autenticación.');
        }
      });
    }

    updateUserBadge();
  }

  // La identidad presentada en la UI procede del servidor, no de datos editables del navegador.
  async function syncAuthenticatedUser() {
    if (!state.token) return;
    try {
      const res = await fetch('/api/v1/auth/me', {
        headers: { 'Authorization': `Bearer ${state.token}` }
      });
      if (!res.ok) throw new Error('Sesión expirada');
      const profile = await res.json();
      state.user.username = profile.username;
      state.user.role = profile.role === 'admin' ? 'Administrador de Plataforma' : 'Auditor de Seguridad';
      state.accessRole = profile.role;
      localStorage.setItem('securecode_user', JSON.stringify(state.user));
      updateUserBadge();
      loadPersistentHistory();
      refreshAdminUsers();
      loadClientSettings();
      loadSubscription();
      loadFinOps();
    } catch {
      state.token = null;
      localStorage.removeItem('securecode_token');
      localStorage.removeItem('securecode_user');
      state.user.username = 'Sesión requerida';
      state.accessRole = null;
      updateUserBadge();
      refreshAdminUsers();
      updateSettingsAccess();
      updateSubscriptionAccess();
      updateFinOpsAccess();
    }
  }

  function openAuthModal() {
    const modal = document.getElementById('authModal');
    removeAuthAlert();
    if (modal) modal.classList.add('active');
  }

  function closeAuthModal() {
    const modal = document.getElementById('authModal');
    removeAuthAlert();
    if (modal) modal.classList.remove('active');
  }

  function showAuthError(message) {
    const form = document.getElementById('loginForm');
    if (!form) return;
    removeAuthAlert();
    const alert = document.createElement('div');
    alert.id = 'authErrorAlert';
    alert.className = 'auth-error-alert';
    alert.setAttribute('role', 'alert');
    alert.textContent = message;
    form.before(alert);
  }

  function removeAuthAlert() {
    document.getElementById('authErrorAlert')?.remove();
  }

  function updateUserBadge() {
    const nameEl = document.getElementById('userProfileName');
    const roleEl = document.getElementById('userProfileRole');
    const avatarEl = document.getElementById('userAvatarInitial');

    const signedIn = Boolean(state.token && state.accessRole);
    if (nameEl) nameEl.textContent = signedIn ? state.user.username : 'Iniciar sesión';
    if (roleEl) roleEl.textContent = signedIn ? state.user.role : 'Acceso seguro requerido';
    if (avatarEl) avatarEl.textContent = signedIn ? state.user.username.charAt(0).toUpperCase() : '?';
  }

})();
