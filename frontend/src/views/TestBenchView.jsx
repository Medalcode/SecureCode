import React, { useState, useEffect } from 'react';
import { 
  FlaskConical, 
  Play, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Clock, 
  ShieldCheck, 
  Copy, 
  Check, 
  RotateCcw, 
  Sliders, 
  GitBranch, 
  Code2, 
  Terminal, 
  Award,
  Layers,
  ChevronRight,
  Database,
  ArrowRight
} from 'lucide-react';
import Navbar from '../components/Navbar';
import { fetchTestBenchCases, runTestBenchCase } from '../api/client';

export default function TestBenchView({ onLogout, onNavigate }) {
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState('GT-GH001-01');
  const [controlFilter, setControlFilter] = useState('Todos');
  const [loadingCases, setLoadingCases] = useState(true);
  
  // Execution state
  const [isRunning, setIsRunning] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [executionHistory, setExecutionHistory] = useState([]);
  const [copiedHash, setCopiedHash] = useState(false);

  // Custom parameters / override mode
  const [customMode, setCustomMode] = useState(false);
  const [customEvidence, setCustomEvidence] = useState({});

  useEffect(() => {
    loadCases();
  }, [controlFilter]);

  const loadCases = async () => {
    setLoadingCases(true);
    const res = await fetchTestBenchCases(controlFilter);
    if (res.success && res.data) {
      setCases(res.data.cases);
      if (res.data.cases.length > 0 && !res.data.cases.some(c => c.case_id === selectedCaseId)) {
        setSelectedCaseId(res.data.cases[0].case_id);
      }
    }
    setLoadingCases(false);
  };

  const currentCase = cases.find(c => c.case_id === selectedCaseId) || cases[0];

  useEffect(() => {
    if (currentCase) {
      setCustomEvidence({ ...currentCase.evidence_preview });
    }
  }, [selectedCaseId, cases]);

  const handleRunTest = async () => {
    if (!currentCase) return;
    setIsRunning(true);
    setLastResult(null);

    const payload = {
      case_id: currentCase.case_id,
      control_id: currentCase.control_id,
      override_evidence: customMode ? customEvidence : null,
    };

    const res = await runTestBenchCase(payload);
    setIsRunning(false);

    if (res.success && res.data) {
      setLastResult(res.data);
      setExecutionHistory(prev => [res.data, ...prev.slice(0, 19)]);
    }
  };

  const handleCopyHash = (hash) => {
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  // Stats calculation
  const totalExecuted = executionHistory.length;
  const totalMatches = executionHistory.filter(h => h.matched).length;
  const accuracyPct = totalExecuted > 0 ? ((totalMatches / totalExecuted) * 100).toFixed(1) : '100.0';
  const avgLatency = totalExecuted > 0 
    ? (executionHistory.reduce((acc, curr) => acc + curr.execution_time_ms, 0) / totalExecuted).toFixed(2)
    : '1.25';

  const getStatusBadge = (status) => {
    switch (status) {
      case 'PASS':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#EBF7EE] text-[#1E7E34] border border-[#C3E6CB]">
            <CheckCircle2 className="w-3.5 h-3.5" />
            PASS (CONFORME)
          </span>
        );
      case 'FAIL':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#FDF2F2] text-[#C0392B] border border-[#F5C6CB]">
            <XCircle className="w-3.5 h-3.5" />
            FAIL (NO CONFORME)
          </span>
        );
      case 'UNKNOWN':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]">
            <AlertTriangle className="w-3.5 h-3.5" />
            UNKNOWN (DESCONOCIDO)
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F6FA] text-slate-800 flex flex-col font-sans">
      <Navbar currentStep="testbench" onNavigate={onNavigate} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex-1">
        {/* Encabezado Principal Stitch */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-blue-50 text-[#213F8B] border border-blue-200">
                <FlaskConical className="w-5 h-5" />
              </span>
              <h1 className="text-2xl font-black text-[#213F8B] tracking-tight">
                BANCO DE PRUEBAS UNITARIO &quot;DE A 1&quot;
              </h1>
            </div>
            <p className="text-sm text-[#555555] mt-1 ml-9">
              Calibración y validación empírica determinista contra Oráculo Ground Truth (Estándar INACAP ES2).
            </p>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span className="px-3 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Oráculo Ground Truth Activo
            </span>
          </div>
        </div>

        {/* Barra de Métricas y Estadísticas de la Sesión */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-xs">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Casos Evaluados</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-black text-[#213F8B]">{totalExecuted}</span>
              <span className="text-xs text-slate-500">ejecuciones</span>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-xs">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Precisión Oráculo</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-black text-emerald-600">{accuracyPct}%</span>
              <span className="text-xs text-emerald-700 font-medium">concordancia</span>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-xs">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Latencia Promedio</span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-black text-slate-800">{avgLatency} ms</span>
              <span className="text-[11px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-mono font-medium">RNF &lt; 500 ms</span>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-xs">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Regla Determinista</span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-base font-bold text-slate-800 truncate">GH-001 / GH-002</span>
              <span className="text-[10px] text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded font-mono font-semibold">v1.0 Strict</span>
            </div>
          </div>
        </div>

        {/* Contenido Principal: Dos Columnas */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Columna Izquierda (5 cols): Selector de Casos Ground Truth */}
          <div className="lg:col-span-5 space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-[#213F8B]" />
                  <h3 className="font-bold text-sm text-slate-800 uppercase tracking-wide">
                    Catálogo de Casos Ground Truth
                  </h3>
                </div>
                <span className="text-xs font-mono font-bold text-slate-500">
                  {cases.length} casos
                </span>
              </div>

              {/* Filtro de Control */}
              <div className="flex gap-1.5 mb-4 p-1 bg-slate-100 rounded-lg text-xs font-medium">
                {['Todos', 'GH-001', 'GH-002'].map((ctl) => (
                  <button
                    key={ctl}
                    onClick={() => setControlFilter(ctl)}
                    className={`flex-1 py-1.5 rounded-md transition cursor-pointer text-center ${
                      controlFilter === ctl
                        ? 'bg-white text-[#213F8B] font-bold shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {ctl}
                  </button>
                ))}
              </div>

              {/* Lista de Casos */}
              <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
                {loadingCases ? (
                  <div className="py-8 text-center text-xs text-slate-400">Cargando catálogo...</div>
                ) : (
                  cases.map((c) => {
                    const isSelected = c.case_id === selectedCaseId;
                    return (
                      <div
                        key={c.case_id}
                        onClick={() => setSelectedCaseId(c.case_id)}
                        className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-blue-50/80 border-[#213F8B] shadow-xs'
                            : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/60'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="font-mono font-bold text-xs text-[#213F8B]">
                            {c.case_id}
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            c.expected_status === 'PASS' 
                              ? 'bg-[#EBF7EE] text-[#1E7E34] border border-[#C3E6CB]'
                              : c.expected_status === 'FAIL'
                              ? 'bg-[#FDF2F2] text-[#C0392B] border border-[#F5C6CB]'
                              : 'bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]'
                          }`}>
                            Oráculo: {c.expected_status}
                          </span>
                        </div>
                        <h4 className="text-xs font-bold text-slate-800 mb-1">{c.title}</h4>
                        <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                          {c.scenario}
                        </p>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Columna Derecha (7 cols): Inspección, Ejecución y Resultados */}
          <div className="lg:col-span-7 space-y-5">
            
            {/* Tarjeta de Inspección de Caso Seleccionado */}
            {currentCase && (
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
                <div className="flex items-start justify-between border-b border-slate-100 pb-4 mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono font-bold text-sm text-[#213F8B] bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                        {currentCase.case_id}
                      </span>
                      <span className="text-xs font-bold text-slate-600">
                        Control: {currentCase.control_id}
                      </span>
                    </div>
                    <h2 className="text-base font-extrabold text-slate-900">{currentCase.title}</h2>
                    <p className="text-xs text-[#555555] mt-1">{currentCase.scenario}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-[11px] text-slate-400 block mb-1">Veredicto Esperado:</span>
                    {getStatusBadge(currentCase.expected_status)}
                  </div>
                </div>

                {/* Parámetros de Evidencia SCM */}
                <div className="mb-5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                      <Code2 className="w-3.5 h-3.5 text-[#213F8B]" />
                      Parámetros de Evidencia de Entrada (Ground Truth)
                    </span>
                    <button
                      onClick={() => setCustomMode(!customMode)}
                      className={`text-xs font-semibold px-2 py-1 rounded transition cursor-pointer flex items-center gap-1 ${
                        customMode 
                          ? 'bg-amber-100 text-amber-800 border border-amber-300' 
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      <Sliders className="w-3 h-3" />
                      {customMode ? 'Modo Calibración Personalizada (Activo)' : 'Editar Valores (Simulación)'}
                    </button>
                  </div>

                  <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-3 font-mono text-xs">
                    <div className="grid grid-cols-2 gap-3 pb-2 border-b border-slate-200/60 text-[11px]">
                      <div>
                        <span className="text-slate-400 block">Repositorio Ficticio/Real:</span>
                        <span className="font-semibold text-slate-700">{currentCase.repository}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">Rama Objetivo:</span>
                        <span className="font-semibold text-slate-700 flex items-center gap-1">
                          <GitBranch className="w-3 h-3 text-slate-400" />
                          {currentCase.branch}
                        </span>
                      </div>
                    </div>

                    {/* Valores de Evidencia para GH-001 */}
                    {currentCase.control_id === 'GH-001' && (
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-[11px] text-slate-500 font-sans font-semibold block mb-1">
                            Aprobaciones Requeridas (approvals):
                          </label>
                          {customMode ? (
                            <input
                              type="number"
                              min="0"
                              max="10"
                              value={customEvidence.required_review_approvals ?? ''}
                              onChange={(e) => setCustomEvidence({
                                ...customEvidence,
                                required_review_approvals: e.target.value === '' ? null : parseInt(e.target.value, 10)
                              })}
                              className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-xs font-mono"
                              placeholder="null (sin reglas)"
                            />
                          ) : (
                            <span className="font-bold text-slate-800 bg-white px-2 py-1 rounded border border-slate-200 inline-block">
                              {customEvidence.required_review_approvals === null ? 'null (No configurado)' : customEvidence.required_review_approvals}
                            </span>
                          )}
                        </div>
                        <div>
                          <label className="text-[11px] text-slate-500 font-sans font-semibold block mb-1">
                            Descarte de Revisiones Obsoletas (dismiss_stale):
                          </label>
                          {customMode ? (
                            <select
                              value={customEvidence.dismiss_stale_reviews === null ? 'null' : String(customEvidence.dismiss_stale_reviews)}
                              onChange={(e) => setCustomEvidence({
                                ...customEvidence,
                                dismiss_stale_reviews: e.target.value === 'null' ? null : e.target.value === 'true'
                              })}
                              className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-xs font-mono"
                            >
                              <option value="true">true (Activado)</option>
                              <option value="false">false (Desactivado)</option>
                              <option value="null">null (No configurado)</option>
                            </select>
                          ) : (
                            <span className="font-bold text-slate-800 bg-white px-2 py-1 rounded border border-slate-200 inline-block">
                              {customEvidence.dismiss_stale_reviews === null ? 'null (No configurado)' : String(customEvidence.dismiss_stale_reviews)}
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Valores de Evidencia para GH-002 */}
                    {currentCase.control_id === 'GH-002' && (
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-[11px] text-slate-500 font-sans font-semibold block mb-1">
                            Rama por Defecto (default_branch):
                          </label>
                          <span className="font-bold text-slate-800 bg-white px-2 py-1 rounded border border-slate-200 inline-block">
                            {customEvidence.default_branch || 'main'}
                          </span>
                        </div>
                        <div>
                          <label className="text-[11px] text-slate-500 font-sans font-semibold block mb-1">
                            Protección Habilitada (protection_enabled):
                          </label>
                          {customMode ? (
                            <select
                              value={customEvidence.protection_enabled === null ? 'null' : String(customEvidence.protection_enabled)}
                              onChange={(e) => setCustomEvidence({
                                ...customEvidence,
                                protection_enabled: e.target.value === 'null' ? null : e.target.value === 'true'
                              })}
                              className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-xs font-mono"
                            >
                              <option value="true">true (Protegida)</option>
                              <option value="false">false (Desprotegida)</option>
                              <option value="null">null (Indeterminada)</option>
                            </select>
                          ) : (
                            <span className="font-bold text-slate-800 bg-white px-2 py-1 rounded border border-slate-200 inline-block">
                              {customEvidence.protection_enabled === null ? 'null (No provisto)' : String(customEvidence.protection_enabled)}
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    <div className="pt-2 text-[11px] text-slate-500 font-sans">
                      <span className="font-semibold text-slate-700">Justificación Técnica del Oráculo: </span>
                      {currentCase.rationale}
                    </div>
                  </div>
                </div>

                {/* Botón de Ejecución "de a 1" */}
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleRunTest}
                    disabled={isRunning}
                    className="flex-1 py-3 px-5 rounded-xl font-bold text-sm text-white bg-[#213F8B] hover:bg-[#1a326f] shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    {isRunning ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                        <span>Ejecutando en Motor Determinista...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-white" />
                        <span>Ejecutar Prueba Unitario &quot;de a 1&quot;</span>
                      </>
                    )}
                  </button>
                  {customMode && (
                    <button
                      onClick={() => setCustomEvidence({ ...currentCase.evidence_preview })}
                      className="px-3.5 py-3 rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 text-xs font-semibold transition cursor-pointer flex items-center gap-1.5"
                      title="Restablecer valores originales del caso"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Restablecer</span>
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Resultado de Ejecución en Tiempo Real */}
            {lastResult && (
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm animate-in fade-in zoom-in duration-150">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-[#213F8B]" />
                    <h3 className="font-bold text-sm text-slate-800 uppercase tracking-wide">
                      Dictamen del Motor Determinista
                    </h3>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-slate-400">Latencia:</span>
                    <span className="font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      {lastResult.execution_time_ms} ms
                    </span>
                  </div>
                </div>

                {/* Veredicto vs Oráculo */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 mb-4 grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 block mb-1 uppercase">Veredicto Motor:</span>
                    {getStatusBadge(lastResult.actual_status)}
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 block mb-1 uppercase">Concordancia con Oráculo:</span>
                    {lastResult.matched ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#EBF7EE] text-[#1E7E34] border border-[#C3E6CB]">
                        <CheckCircle2 className="w-4 h-4" />
                        100% MATCH (CONCORDANCIA TOTAL)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FDF2F2] text-[#C0392B] border border-[#F5C6CB]">
                        <XCircle className="w-4 h-4" />
                        DISCREPANCIA CON ORÁCULO
                      </span>
                    )}
                  </div>
                </div>

                {/* Explicación y Hash Canónico */}
                <div className="space-y-3 text-xs">
                  <div className="bg-blue-50/60 p-3 rounded-lg border border-blue-100 text-slate-700 leading-relaxed">
                    <strong className="text-[#213F8B] block mb-0.5">Dictamen de Evaluación:</strong>
                    {lastResult.explanation}
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-[11px]">
                    <div>
                      <span className="text-slate-400 block">Regla Evaluada:</span>
                      <span className="font-mono font-semibold text-slate-800">{lastResult.rule_applied}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Timestamp UTC:</span>
                      <span className="font-mono text-slate-700">{lastResult.evaluated_at}</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] font-semibold text-slate-500">Hash Canónico de Evidencia (SHA-256):</span>
                      <button
                        onClick={() => handleCopyHash(lastResult.integrity_hash)}
                        className="text-[10px] text-[#213F8B] hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        {copiedHash ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                        {copiedHash ? 'Copiado' : 'Copiar Hash'}
                      </button>
                    </div>
                    <div className="p-2 rounded bg-slate-100 font-mono text-[10px] break-all text-slate-700 select-all border border-slate-200">
                      {lastResult.integrity_hash}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Historial de Ejecuciones de la Sesión */}
            {executionHistory.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
                <h4 className="font-bold text-xs text-slate-700 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  Registro de Pruebas Ejecutadas en Esta Sesión ({executionHistory.length})
                </h4>
                <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto pr-1">
                  {executionHistory.map((h, i) => (
                    <div key={i} className="py-2.5 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-slate-700">{h.case_id}</span>
                        <span className="text-slate-400">|</span>
                        <span className="text-slate-600">{h.control_id}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-[11px] text-slate-500">{h.execution_time_ms} ms</span>
                        {h.matched ? (
                          <span className="text-emerald-700 font-bold text-[11px] bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            MATCH
                          </span>
                        ) : (
                          <span className="text-red-700 font-bold text-[11px] bg-red-50 px-2 py-0.5 rounded border border-red-200">
                            MISMATCH
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>

        </div>

      </main>
    </div>
  );
}
