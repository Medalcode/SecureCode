import React, { useState } from 'react';
import { clearSession } from '../api/client';
import { 
  CheckCircle2, 
  XCircle, 
  HelpCircle, 
  AlertTriangle, 
  Copy, 
  Check, 
  ArrowLeft, 
  RotateCcw, 
  History,
  FileDown
} from 'lucide-react';
import Navbar from '../components/Navbar';
import ExportAuditModal from '../components/ExportAuditModal';

export default function ResultadoView({ 
  resultData, 
  controlId = 'GH-001', 
  onLogout, 
  onNewEvaluation,
  onNavigate
}) {
  const [copied, setCopied] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);

  const handleLogout = () => {
    clearSession();
    if (onLogout) {
      onLogout();
    }
  };

  const handleCopyHash = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Determinar el estado REAL devuelto por la evaluación
  const isErrorState = Boolean(resultData?.isError);
  const rawStatus = (resultData?.status || '').toUpperCase();
  const state = isErrorState ? 'ERROR' : (['PASS', 'FAIL', 'UNKNOWN'].includes(rawStatus) ? rawStatus : 'UNKNOWN');

  // Metadatos calculados del resultado
  const isGH002 = controlId === 'GH-002' || resultData?.control_id === 'GH-002';
  const controlName = isGH002 
    ? 'GH-002 Protección de rama' 
    : 'GH-001 Revisión por pares';

  const repoDisplay = resultData?.source?.repository 
    ? `${resultData.source.repository} (${resultData.source.branch || 'main'})`
    : 'acme-corp/payment-gateway (main)';

  const evalDate = resultData?.evaluated_at
    ? new Date(resultData.evaluated_at).toUTCString().replace('GMT', 'UTC')
    : new Date().toUTCString().replace('GMT', 'UTC');

  const evalId = resultData?.evaluation_id || 'eval_9f8a2b3c';
  const evidenceHash = resultData?.evidence?.hash || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';

  // Configuración de textos y estilos según el estado automático recibido
  const configByState = {
    PASS: {
      description: 'Control cumple',
      badge: 'CONFORME',
      badgeBg: '#EBF7EE',
      badgeBorder: '#C3E6CB',
      badgeText: '#1E7E34',
      icon: CheckCircle2,
      suggestedAction: 'Sin acción correctiva requerida.',
      approvals: resultData?.evidence?.required_review_approvals ?? 2,
      dismissStale: resultData?.evidence?.dismiss_stale_reviews === false ? 'No' : 'Sí',
      protectionEnabled: 'Sí',
      defaultBranch: resultData?.evidence?.default_branch || 'main',
    },
    FAIL: {
      description: 'Control no cumple',
      badge: 'NO CONFORME',
      badgeBg: '#FDF2F2',
      badgeBorder: '#F5C6CB',
      badgeText: '#C0392B',
      icon: XCircle,
      suggestedAction: 'Ajuste la configuración en GitHub y vuelva a evaluar.',
      approvals: resultData?.evidence?.required_review_approvals ?? 1,
      dismissStale: resultData?.evidence?.dismiss_stale_reviews ? 'Sí' : 'No',
      protectionEnabled: 'No',
      defaultBranch: resultData?.evidence?.default_branch || 'main',
    },
    UNKNOWN: {
      description: 'Sin datos suficientes',
      badge: 'DESCONOCIDO',
      badgeBg: '#FFFBEB',
      badgeBorder: '#FDE68A',
      badgeText: '#B45309',
      icon: AlertTriangle,
      suggestedAction: 'Verifique permisos del token o existencia de rama/repo.',
      approvals: 'No configurado',
      dismissStale: 'No configurado',
      protectionEnabled: 'No configurado',
      defaultBranch: resultData?.evidence?.default_branch || 'main',
    },
    ERROR: {
      description: 'Servicio no disponible',
      badge: 'ERROR SERVICIO',
      badgeBg: '#FDF2F2',
      badgeBorder: '#F5C6CB',
      badgeText: '#C0392B',
      icon: AlertTriangle,
      suggestedAction: 'Intente nuevamente más tarde o verifique la conexión con el servidor.',
      message: resultData?.message || 'Servicio no disponible. No se registró ninguna evaluación. Intente nuevamente más tarde.',
    }
  };

  const current = configByState[state] || configByState.UNKNOWN;
  const StateIcon = current.icon;

  return (
    <div 
      className="min-h-screen w-full flex flex-col font-sans"
      style={{ backgroundColor: '#F4F6FA' }}
    >
      {/* Barra de Navegación Unificada Stitch */}
      <Navbar currentStep="resultado" onNavigate={onNavigate} />

      {/* Contenedor Principal */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
        <div 
          className="w-full max-w-[520px] bg-white border border-slate-200 shadow-md p-6 sm:p-8"
          style={{ borderRadius: '8px' }}
        >
          {/* CASO: ERROR (Servicio no disponible) */}
          {state === 'ERROR' ? (
            <div className="space-y-6 animate-in fade-in duration-150">
              <div 
                className="p-4 rounded-lg flex items-start gap-3 border"
                style={{
                  backgroundColor: current.badgeBg,
                  borderColor: current.badgeBorder,
                  color: current.badgeText,
                }}
              >
                <StateIcon className="w-5 h-5 shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-bold text-sm">Servicio no disponible</h3>
                  <p className="text-xs mt-1 leading-relaxed">{current.message}</p>
                </div>
              </div>

              <div className="space-y-2">
                <button
                  onClick={onNewEvaluation}
                  className="w-full py-2.5 px-4 font-semibold text-sm transition shadow-sm hover:opacity-95 active:opacity-90 cursor-pointer flex items-center justify-center gap-2"
                  style={{
                    backgroundColor: '#213F8B',
                    color: '#FFFFFF',
                    borderRadius: '8px',
                  }}
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Reintentar evaluación</span>
                </button>

                <button
                  onClick={() => onNavigate && onNavigate('historial')}
                  className="w-full py-2.5 px-4 font-semibold text-xs transition border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg flex items-center justify-center gap-2 cursor-pointer"
                >
                  <History className="w-4 h-4 text-slate-500" />
                  <span>Ir al Historial de Auditorías</span>
                </button>
              </div>
            </div>
          ) : (
            /* CASOS NORMALES: PASS, FAIL, UNKNOWN */
            <div className="space-y-6 animate-in fade-in duration-150">
              
              {/* Sección: ESTADO DE LA EVALUACIÓN */}
              <div>
                <h3 
                  className="text-[11px] font-bold tracking-wider mb-2 uppercase"
                  style={{ color: '#213F8B' }}
                >
                  ESTADO DE LA EVALUACIÓN
                </h3>
                <div 
                  className="p-4 rounded-lg flex items-center justify-between border"
                  style={{
                    backgroundColor: current.badgeBg,
                    borderColor: current.badgeBorder,
                  }}
                >
                  <div className="flex items-center gap-3">
                    <StateIcon 
                      className="w-5 h-5" 
                      style={{ color: current.badgeText }} 
                    />
                    <div>
                      <h4 
                        className="font-bold text-sm"
                        style={{ color: current.badgeText }}
                      >
                        {state}
                      </h4>
                      <p 
                        className="text-xs"
                        style={{ color: '#555555' }}
                      >
                        {current.description}
                      </p>
                    </div>
                  </div>
                  
                  {/* Badge Conforme / No Conforme / Desconocido */}
                  <span 
                    className="text-xs font-bold px-2.5 py-1 rounded"
                    style={{
                      backgroundColor: '#FFFFFF',
                      color: current.badgeText,
                      border: `1px solid ${current.badgeBorder}`,
                    }}
                  >
                    {current.badge}
                  </span>
                </div>
              </div>

              {/* Sección: METADATOS DE LA EVALUACIÓN */}
              <div>
                <h3 
                  className="text-[11px] font-bold tracking-wider mb-2 uppercase"
                  style={{ color: '#213F8B' }}
                >
                  METADATOS DE LA EVALUACIÓN
                </h3>
                <div className="border border-slate-200 rounded-lg p-3 bg-white space-y-2 text-xs">
                  <div className="flex justify-between items-center py-1 border-b border-slate-100">
                    <span style={{ color: '#555555' }}>Control:</span>
                    <span className="font-semibold text-slate-800">{controlName}</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-100">
                    <span style={{ color: '#555555' }}>Repositorio:</span>
                    <span className="font-medium text-slate-800">{repoDisplay}</span>
                  </div>
                  <div className="flex justify-between items-center py-1">
                    <span style={{ color: '#555555' }}>Fecha (UTC):</span>
                    <span className="font-mono text-slate-700">{evalDate}</span>
                  </div>
                </div>
              </div>

              {/* Sección: EVIDENCIA RECOLECTADA */}
              <div>
                <h3 
                  className="text-[11px] font-bold tracking-wider mb-2 uppercase"
                  style={{ color: '#213F8B' }}
                >
                  EVIDENCIA RECOLECTADA
                </h3>
                <div className="border border-slate-200 rounded-lg p-3 bg-white space-y-2 text-xs">
                  {!isGH002 ? (
                    <>
                      <div className="flex justify-between items-center py-1 border-b border-slate-100">
                        <span style={{ color: '#555555' }}>Aprobaciones requeridas:</span>
                        <span className="font-semibold text-slate-800">{current.approvals}</span>
                      </div>
                      <div className="flex justify-between items-center py-1">
                        <span style={{ color: '#555555' }}>Descartar aprobaciones obsoletas:</span>
                        <span className="font-semibold text-slate-800">{current.dismissStale}</span>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="flex justify-between items-center py-1 border-b border-slate-100">
                        <span style={{ color: '#555555' }}>Rama por defecto:</span>
                        <span className="font-semibold text-slate-800">{current.defaultBranch}</span>
                      </div>
                      <div className="flex justify-between items-center py-1">
                        <span style={{ color: '#555555' }}>Protección de rama habilitada:</span>
                        <span className="font-semibold text-slate-800">{current.protectionEnabled}</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Sección: INTEGRIDAD */}
              <div>
                <h3 
                  className="text-[11px] font-bold tracking-wider mb-2 uppercase"
                  style={{ color: '#213F8B' }}
                >
                  INTEGRIDAD
                </h3>
                <div className="border border-slate-200 rounded-lg p-3 bg-white space-y-2 text-xs">
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span style={{ color: '#555555' }}>Hash SHA-256 de evidencia:</span>
                      <button
                        type="button"
                        onClick={() => handleCopyHash(evidenceHash)}
                        className="inline-flex items-center gap-1 text-[11px] text-[#213F8B] hover:underline cursor-pointer"
                        title="Copiar hash"
                      >
                        {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                        <span>{copied ? 'Copiado' : 'Copiar'}</span>
                      </button>
                    </div>
                    <p className="font-mono text-[11px] text-slate-600 bg-slate-50 p-2 rounded border border-slate-200 break-all select-all">
                      {evidenceHash}
                    </p>
                  </div>

                  <div className="flex justify-between items-center pt-1 border-t border-slate-100 text-[11px]">
                    <span style={{ color: '#555555' }}>ID de Evaluación:</span>
                    <span className="font-mono text-slate-700">{evalId}</span>
                  </div>
                </div>
              </div>

              {/* Acción Sugerida */}
              <div 
                className="p-3 rounded-lg text-xs"
                style={{ backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0' }}
              >
                <span className="font-semibold text-slate-700">Acción sugerida: </span>
                <span style={{ color: '#555555' }}>{current.suggestedAction}</span>
              </div>

              {/* Botones de Acción */}
              <div className="pt-2 space-y-2">
                {/* Botón Principal de Exportar Reporte PDF / Despacho (Prioridad 4) */}
                <button
                  type="button"
                  onClick={() => setExportModalOpen(true)}
                  className="w-full py-2.5 px-4 font-semibold text-xs transition bg-blue-50 border border-blue-200 text-[#213F8B] hover:bg-blue-100 rounded-lg flex items-center justify-center gap-2 cursor-pointer shadow-2xs"
                >
                  <FileDown className="w-4 h-4 text-[#213F8B]" />
                  <span>Exportar Reporte de Auditoría (PDF / Correo)</span>
                </button>

                <button
                  type="button"
                  onClick={onNewEvaluation}
                  className="w-full py-2.5 px-4 font-semibold text-sm transition shadow-sm hover:opacity-95 active:opacity-90 cursor-pointer flex items-center justify-center gap-2"
                  style={{
                    backgroundColor: '#213F8B',
                    color: '#FFFFFF',
                    borderRadius: '8px',
                  }}
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Nueva evaluación</span>
                </button>

                <button
                  type="button"
                  onClick={() => onNavigate && onNavigate('historial')}
                  className="w-full py-2.5 px-4 font-semibold text-xs transition border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg flex items-center justify-center gap-2 cursor-pointer"
                >
                  <History className="w-4 h-4 text-slate-500" />
                  <span>Ver Historial de Auditorías</span>
                </button>
              </div>

            </div>
          )}
        </div>
      </main>

      {/* Modal Stitch de Exportar Reporte de Auditoría */}
      <ExportAuditModal
        isOpen={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        initialData={{
          control: controlName,
          repository: repoDisplay,
          verdict: `${state} (${current.badge})`,
          integrityHash: evidenceHash,
          evaluationId: evalId
        }}
      />
    </div>
  );
}
