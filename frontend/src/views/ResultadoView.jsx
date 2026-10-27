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
  RotateCcw
} from 'lucide-react';

export default function ResultadoView({ 
  resultData, 
  controlId = 'GH-001', 
  onLogout, 
  onNewEvaluation 
}) {
  const [copied, setCopied] = useState(false);

  // Determinar estado base (PASS, FAIL, UNKNOWN o ERROR)
  const initialStatus = resultData?.status 
    ? resultData.status.toUpperCase() 
    : (resultData?.isError ? 'ERROR' : 'PASS');

  // Permitir alternar entre las 4 variantes oficiales para demostración / presentación
  const [activeVariant, setActiveVariant] = useState(initialStatus);

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

  // Metadatos calculados de la evaluación
  const isGH002 = controlId === 'GH-002' || resultData?.control_id === 'GH-002';
  const controlName = isGH002 
    ? 'GH-002 Protección de rama' 
    : 'GH-001 Revisión por pares';

  const repoDisplay = resultData?.source?.repository 
    ? `${resultData.source.repository} (${resultData.source.branch || 'main'})`
    : 'acme-corp/payment-gateway (main)';

  const evalDate = resultData?.evaluated_at
    ? new Date(resultData.evaluated_at).toUTCString().replace('GMT', 'UTC')
    : '2025-05-18 14:32 UTC';

  const evalId = resultData?.evaluation_id || 'eval_9f8a2b3c4d5e';
  const evidenceHash = resultData?.evidence?.hash || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';

  // Configuración de las 4 variantes oficiales (Imágenes 1 a 4 del informe)
  const variantConfig = {
    PASS: {
      state: 'PASS',
      description: 'Control cumple',
      badge: 'CONFORME',
      badgeBg: '#EBF7EE',
      badgeBorder: '#C3E6CB',
      badgeText: '#1E7E34',
      icon: CheckCircle2,
      suggestedAction: 'Sin acción correctiva requerida.',
      approvals: resultData?.evidence?.required_review_approvals ?? 2,
      dismissStale: resultData?.evidence?.dismiss_stale_reviews ? 'Sí' : 'Sí',
    },
    FAIL: {
      state: 'FAIL',
      description: 'Control no cumple',
      badge: 'NO CONFORME',
      badgeBg: '#FDF2F2',
      badgeBorder: '#F5C6CB',
      badgeText: '#C0392B',
      icon: XCircle,
      suggestedAction: 'Ajuste la configuración en GitHub y vuelva a evaluar.',
      approvals: resultData?.evidence?.required_review_approvals ?? 1,
      dismissStale: 'No',
    },
    UNKNOWN: {
      state: 'UNKNOWN',
      description: 'Evidencia insuficiente',
      message: 'No fue posible determinar el estado con certeza',
      badge: 'DESCONOCIDO',
      badgeBg: '#FFFBEB',
      badgeBorder: '#FDE68A',
      badgeText: '#B45309',
      icon: HelpCircle,
      suggestedAction: 'Verifique permisos del token y que el repositorio y la rama existan; luego reintente.',
      approvals: 'No disponible',
      dismissStale: 'No disponible',
    },
    ERROR: {
      state: 'ERROR',
      message: 'Servicio no disponible. No se registró ninguna evaluación. Intente nuevamente más tarde.',
      badgeBg: '#FDF2F2',
      badgeBorder: '#F5C6CB',
      badgeText: '#C0392B',
      icon: AlertTriangle,
      actionText: 'Reintentar',
    }
  };

  const current = variantConfig[activeVariant] || variantConfig.PASS;
  const StateIcon = current.icon;

  return (
    <div 
      className="min-h-screen w-full flex flex-col font-sans"
      style={{ backgroundColor: '#F4F6FA' }}
    >
      {/* Barra Superior / Encabezado */}
      <header className="w-full bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span 
              className="font-extrabold text-lg tracking-wide"
              style={{ color: '#213F8B' }}
            >
              SECURECODE
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-sm font-medium text-slate-700">
              Resultado de la evaluación
            </span>
          </div>

          <button
            onClick={handleLogout}
            className="text-xs font-medium px-3 py-1.5 rounded transition hover:bg-slate-100 cursor-pointer"
            style={{ color: '#555555' }}
          >
            Cerrar sesión
          </button>
        </div>
      </header>

      {/* Selector de demostración de las 4 Variantes Oficiales (Tabla 19) */}
      <div className="max-w-xl mx-auto px-4 pt-4 w-full flex items-center justify-center gap-1.5 text-xs">
        <span className="text-slate-400 text-[11px] mr-1 hidden sm:inline">Variantes Tabla 19:</span>
        {['PASS', 'FAIL', 'UNKNOWN', 'ERROR'].map((v) => (
          <button
            key={v}
            onClick={() => setActiveVariant(v)}
            className={`px-2.5 py-1 rounded text-[11px] font-semibold transition border cursor-pointer ${
              activeVariant === v 
                ? 'bg-slate-800 text-white border-slate-800 shadow-sm' 
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
            }`}
          >
            {v === 'PASS' && '🟢 PASS'}
            {v === 'FAIL' && '🔴 FAIL'}
            {v === 'UNKNOWN' && '🟡 UNKNOWN'}
            {v === 'ERROR' && '⚪ ERROR'}
          </button>
        ))}
      </div>

      {/* Contenedor Principal */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
        <div 
          className="w-full max-w-[520px] bg-white border border-slate-200 shadow-md p-6 sm:p-8"
          style={{ borderRadius: '8px' }}
        >
          {/* VARIANTE 4: ERROR (Servicio no disponible) */}
          {activeVariant === 'ERROR' ? (
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
                  <h3 className="font-bold text-sm">Falla de Comunicación</h3>
                  <p className="text-xs mt-1 leading-relaxed">{current.message}</p>
                </div>
              </div>

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
                <span>Reintentar</span>
              </button>
            </div>
          ) : (
            /* VARIANTES 1, 2 Y 3: PASS, FAIL Y UNKNOWN */
            <div className="space-y-5 animate-in fade-in duration-150">
              
              {/* Banner de Estado (Status Banner) */}
              <div 
                className="p-3.5 rounded-lg flex items-center justify-between border"
                style={{
                  backgroundColor: current.badgeBg,
                  borderColor: current.badgeBorder,
                }}
              >
                <div className="flex items-center gap-2.5">
                  <StateIcon className="w-5 h-5" style={{ color: current.badgeText }} />
                  <div>
                    <h2 
                      className="font-bold text-sm tracking-wide"
                      style={{ color: current.badgeText }}
                    >
                      {current.state}: {current.description}
                    </h2>
                    {current.message && (
                      <p className="text-[11px] text-amber-800 font-normal mt-0.5">
                        {current.message}
                      </p>
                    )}
                  </div>
                </div>

                <span 
                  className="px-2 py-0.5 text-[11px] font-extrabold uppercase rounded border tracking-wider"
                  style={{
                    backgroundColor: '#FFFFFF',
                    borderColor: current.badgeBorder,
                    color: current.badgeText,
                  }}
                >
                  {current.badge}
                </span>
              </div>

              {/* Sección: DETALLES */}
              <div className="border border-slate-200 rounded-lg p-3.5 bg-slate-50/50 space-y-1.5 text-xs">
                <div className="flex justify-between py-0.5">
                  <span style={{ color: '#555555' }}>Control:</span>
                  <span className="font-semibold text-slate-800">{controlName}</span>
                </div>
                <div className="flex justify-between py-0.5">
                  <span style={{ color: '#555555' }}>Repositorio:</span>
                  <span className="font-mono text-slate-800">{repoDisplay}</span>
                </div>
                <div className="flex justify-between py-0.5">
                  <span style={{ color: '#555555' }}>Fecha evaluación:</span>
                  <span className="text-slate-700">{evalDate}</span>
                </div>
              </div>

              {/* Sección: EVIDENCIA OBTENIDA */}
              <div>
                <h3 
                  className="text-[11px] font-bold tracking-wider mb-2 uppercase"
                  style={{ color: '#213F8B' }}
                >
                  EVIDENCIA OBTENIDA
                </h3>
                <div className="border border-slate-200 rounded-lg p-3.5 bg-white space-y-2 text-xs">
                  {isGH002 ? (
                    <>
                      <div className="flex justify-between py-0.5 border-b border-slate-100">
                        <span style={{ color: '#555555' }}>Rama por defecto:</span>
                        <span className="font-semibold text-slate-800">
                          {activeVariant === 'UNKNOWN' ? 'No disponible' : 'main'}
                        </span>
                      </div>
                      <div className="flex justify-between py-0.5">
                        <span style={{ color: '#555555' }}>Protección habilitada:</span>
                        <span className="font-semibold text-slate-800">
                          {activeVariant === 'PASS' ? 'Sí' : activeVariant === 'FAIL' ? 'No' : 'No disponible'}
                        </span>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="flex justify-between py-0.5 border-b border-slate-100">
                        <span style={{ color: '#555555' }}>Aprobaciones requeridas (required_approvals):</span>
                        <span className="font-semibold text-slate-800">{current.approvals}</span>
                      </div>
                      <div className="flex justify-between py-0.5">
                        <span style={{ color: '#555555' }}>Descartar revisiones obsoletas (dismiss_stale):</span>
                        <span className="font-semibold text-slate-800">{current.dismissStale}</span>
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

              {/* Botón: Nueva Evaluación */}
              <div className="pt-2">
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
              </div>

            </div>
          )}
        </div>
      </main>
    </div>
  );
}
