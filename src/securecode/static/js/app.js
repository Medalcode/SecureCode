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
      username: 'auditor@demo.org',
      role: 'Auditor de Seguridad',
      plan: 'Enterprise Academic',
      usedQuota: 4104,
      maxQuota: 20480, // Basado en el análisis de 500 MB de Supabase en el informe ES2
      slaAvailability: '99.5%'
    },
    activeTab: 'evaluator',
    selectedControl: 'GH-001',
    evalHistory: JSON.parse(localStorage.getItem('securecode_history') || '[]'),
    systemHealth: { status: 'checking', latencyMs: null },
    rules: [
      {
        control_id: 'GH-001',
        name: 'Branch Review Policy',
        description: 'Exige un mínimo de 2 revisiones aprobadas y descarte de revisiones obsoletas en ramas protegidas.',
        rule_file: 'rules/GH-001.json',
        operators: 'AND(required_review_approvals GTE 2, dismiss_stale_reviews EQ true)'
      },
      {
        control_id: 'GH-002',
        name: 'Default Branch Protection',
        description: 'Exige que la rama por defecto del repositorio cuente con protección de rama habilitada.',
        rule_file: 'rules/GH-002.json',
        operators: 'protection_enabled EQ true'
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
    initAdminConsole();
    initAuthModal();
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
    const controlButtons = document.querySelectorAll('.control-btn');
    const branchGroup = document.getElementById('branchInputGroup');
    const form = document.getElementById('evaluatorForm');
    const btnSubmit = document.getElementById('btnSubmitEval');
    const repoInput = document.getElementById('repoInput');
    const branchInput = document.getElementById('branchInput');
    const chips = document.querySelectorAll('.chip-btn');

    // Selector de control
    controlButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        controlButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.selectedControl = btn.dataset.control;

        // GH-002 evalúa la rama por defecto, oculta el input manual de branch
        if (state.selectedControl === 'GH-002') {
          if (branchGroup) branchGroup.style.display = 'none';
        } else {
          if (branchGroup) branchGroup.style.display = 'flex';
        }
      });
    });

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

      if (!rawRepo || !rawRepo.includes('/')) {
        alert('Por favor especifica el repositorio en formato "owner/repo" (ej: Medalcode/SecureCode).');
        repoInput.focus();
        return;
      }

      const [owner, repository] = rawRepo.split('/');

      btnSubmit.disabled = true;
      btnSubmit.innerHTML = `
        <svg class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
          <path d="M12 2a10 10 0 0 1 10 10"></path>
        </svg>
        <span>Evaluando evidencia...</span>
      `;

      try {
        await executeEvaluation(state.selectedControl, owner, repository, branch);
      } catch (err) {
        renderErrorResult(err.message);
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
          <span>Ejecutar Evaluación Determinista</span>
        `;
      }
    });

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

    // Botón de nueva evaluación desde tarjeta de resultados
    const btnResetResult = document.getElementById('btnResetResult');
    if (btnResetResult) {
      btnResetResult.addEventListener('click', () => {
        document.getElementById('resultContainer').classList.remove('active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
  }

  // --- Ejecución de la Petición al Backend ---
  async function executeEvaluation(controlId, owner, repo, branch) {
    const isGH001 = controlId === 'GH-001';
    const endpoint = isGH001 ? '/api/v1/evaluations/gh-001' : '/api/v1/evaluations/gh-002';
    const payload = isGH001
      ? { owner, repository: repo, branch: branch || 'main' }
      : { owner, repository: repo };

    const customToken = localStorage.getItem('securecode_custom_gh_token');
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };

    if (state.token) {
      headers['Authorization'] = `Bearer ${state.token}`;
    }
    if (customToken) {
      headers['X-GitHub-Token'] = customToken;
    }

    const res = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    });

    if (res.status === 401) {
      openAuthModal('Se requiere autenticación para evaluar controles en el servidor.');
      throw new Error('401 No autorizado: inicie sesión con credenciales válidas.');
    }

    if (res.status === 502) {
      renderServiceUnavailable('Falla de infraestructura o comunicación ascendente con la API de GitHub (HTTP 502). No se registró evaluación parcial.');
      return;
    }

    if (res.status === 422) {
      throw new Error('422 Error de validación: el repositorio o la rama indicada no pudieron ser normalizados.');
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
    document.getElementById('resRepository').textContent = `${data.source.repository} (${data.source.branch})`;
    document.getElementById('resEvaluatedAt').textContent = new Date(data.evaluated_at).toLocaleString();
    document.getElementById('resEvaluationId').textContent = data.evaluation_id;
    document.getElementById('resultHashText').textContent = data.evidence.hash;

    // JSON Payload
    document.getElementById('jsonPayloadBody').textContent = JSON.stringify(data, null, 2);

    container.classList.add('active');
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function renderAction(text) {
    const actionEl = document.getElementById('resultActionText');
    if (actionEl) actionEl.textContent = text;
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
    alert(`Error al procesar la evaluación:\n${msg}`);
  }

  // --- Historial Local de Evaluaciones (Estilo Chat sidebar) ---
  function initHistory() {
    renderHistoryList();
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
          <span style="font-weight:600;">${item.control}</span>
          <span style="text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">${item.repo}</span>
        </div>
        <span style="font-size:10px; color:var(--text-faint);">${item.time}</span>
      </div>
    `).join('');

    list.querySelectorAll('.history-item').forEach(el => {
      el.addEventListener('click', () => {
        const idx = el.dataset.idx;
        const record = state.evalHistory[idx];
        if (record && record.data) {
          renderEvaluationResult(record.data);
          document.querySelectorAll('.history-item').forEach(h => h.classList.remove('active'));
          el.classList.add('active');
        }
      });
    });
  }

  // --- FinOps y Cuota de Consumo ---
  function initDashboard() {
    updateQuotaUI();
  }

  function incrementUsedQuota() {
    state.user.usedQuota += 1;
    localStorage.setItem('securecode_user', JSON.stringify(state.user));
    updateQuotaUI();
  }

  function updateQuotaUI() {
    const used = state.user.usedQuota;
    const max = state.user.maxQuota;
    const pct = Math.min(Math.round((used / max) * 100), 100);

    const txtUsed = document.getElementById('quotaUsedText');
    const txtMax = document.getElementById('quotaMaxText');
    const barFill = document.getElementById('quotaBarFill');
    const statPct = document.getElementById('quotaPctText');

    if (txtUsed) txtUsed.textContent = used.toLocaleString();
    if (txtMax) txtMax.textContent = max.toLocaleString();
    if (barFill) barFill.style.width = `${pct}%`;
    if (statPct) statPct.textContent = `${pct}% consumido`;
  }

  // --- Consola de Administración ---
  function initAdminConsole() {
    const btnSimulate = document.getElementById('btnSimulateAudit');
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
    const btnDemoLogin = document.getElementById('btnDemoLogin');
    const btnCloseModal = document.getElementById('btnCloseAuthModal');
    const btnOpenLogin = document.getElementById('btnOpenLogin');

    if (btnOpenLogin) {
      btnOpenLogin.addEventListener('click', () => openAuthModal());
    }

    if (btnCloseModal) {
      btnCloseModal.addEventListener('click', () => closeAuthModal());
    }

    if (btnDemoLogin) {
      btnDemoLogin.addEventListener('click', async () => {
        // En modo demostración, genera una sesión segura o usa token mock
        state.token = 'demo-bearer-token-academic-es2';
        state.user.username = 'auditor.demo@securecode.inacap';
        localStorage.setItem('securecode_token', state.token);
        localStorage.setItem('securecode_user', JSON.stringify(state.user));
        updateUserBadge();
        closeAuthModal();
      });
    }

    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const user = document.getElementById('authUsername').value.trim();
        const pass = document.getElementById('authPassword').value;
        const errAlert = document.getElementById('authErrorAlert');

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
            if (errAlert) {
              errAlert.style.display = 'block';
              errAlert.textContent = 'Usuario o contraseña incorrectos. Verifique sus credenciales.';
            }
            return;
          }

          const data = await res.json();
          state.token = data.access_token;
          state.user.username = user;
          localStorage.setItem('securecode_token', state.token);
          localStorage.setItem('securecode_user', JSON.stringify(state.user));
          updateUserBadge();
          closeAuthModal();
        } catch (error) {
          if (errAlert) {
            errAlert.style.display = 'block';
            errAlert.textContent = 'Error al comunicarse con el servicio de autenticación.';
          }
        }
      });
    }

    updateUserBadge();
  }

  function openAuthModal(msg) {
    const modal = document.getElementById('authModal');
    const alert = document.getElementById('authErrorAlert');
    if (alert) {
      alert.style.display = msg ? 'block' : 'none';
      if (msg) alert.textContent = msg;
    }
    if (modal) modal.classList.add('active');
  }

  function closeAuthModal() {
    const modal = document.getElementById('authModal');
    if (modal) modal.classList.remove('active');
  }

  function updateUserBadge() {
    const nameEl = document.getElementById('userProfileName');
    const roleEl = document.getElementById('userProfileRole');
    const avatarEl = document.getElementById('userAvatarInitial');

    if (nameEl && state.user) nameEl.textContent = state.user.username;
    if (roleEl && state.user) roleEl.textContent = state.user.role;
    if (avatarEl && state.user) avatarEl.textContent = state.user.username.charAt(0).toUpperCase();
  }

})();
