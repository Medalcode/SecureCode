import React, { useState } from 'react';
import { 
  FileDown, 
  Send, 
  ShieldCheck, 
  Mail, 
  CheckCircle2, 
  X, 
  Loader2, 
  Check, 
  Lock, 
  Copy,
  ExternalLink,
  Download
} from 'lucide-react';
import { exportAuditReport, getAuditPdfDownloadUrl } from '../api/client';

export default function ExportAuditModal({
  isOpen,
  onClose,
  initialData = {}
}) {
  if (!isOpen) return null;

  const control = initialData.control || 'GH-001 Revisión por pares';
  const repository = initialData.repository || 'acme-corp/payment-gateway (main)';
  const verdict = initialData.verdict || 'UNKNOWN (DESCONOCIDO)';
  const integrityHash = initialData.integrityHash || initialData.hash || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
  const evaluationId = initialData.evaluationId || initialData.evaluation_id || 'eval_9f8a2b3c';

  const [generatePdf, setGeneratePdf] = useState(true);
  const [email, setEmail] = useState('josemorahj23@gmail.com');
  const [isLoading, setIsLoading] = useState(false);
  const [successReceipt, setSuccessReceipt] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [copiedHash, setCopiedHash] = useState(false);

  const handleCopyHash = () => {
    navigator.clipboard.writeText(integrityHash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const triggerDirectPdfDownload = async () => {
    try {
      const downloadUrl = getAuditPdfDownloadUrl({
        control,
        repository,
        verdict,
        hash: integrityHash,
        evaluation_id: evaluationId,
        email: email.trim()
      });
      const resp = await fetch(downloadUrl);
      if (resp.ok) {
        const blob = await resp.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `Dictamen_Auditoria_${evaluationId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(blobUrl);
        a.remove();
      } else {
        window.open(downloadUrl, '_blank');
      }
    } catch (e) {
      console.error("Direct PDF trigger error:", e);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage('');
    setSuccessReceipt(null);

    const payload = {
      evaluation_id: evaluationId,
      evaluated_control: control,
      repository: repository,
      verdict: verdict,
      integrity_hash: integrityHash,
      generate_pdf: generatePdf,
      email: email.trim(),
    };

    const res = await exportAuditReport(payload);
    setIsLoading(false);

    if (res.success && res.data) {
      setSuccessReceipt(res.data);
      if (generatePdf) {
        await triggerDirectPdfDownload();
      }
    } else {
      setErrorMessage(res.message || 'No fue posible completar la exportación.');
    }
  };

  const getVerdictStyle = () => {
    const v = verdict.toUpperCase();
    if (v.includes('PASS') || v.includes('CONFORME')) {
      return 'bg-[#EBF7EE] text-[#1E7E34] border-[#C3E6CB]';
    }
    if (v.includes('FAIL') || v.includes('NO CONFORME')) {
      return 'bg-[#FDF2F2] text-[#C0392B] border-[#F5C6CB]';
    }
    return 'bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]';
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div 
        className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 animate-in fade-in zoom-in duration-150 relative text-slate-800"
        style={{ borderRadius: '12px' }}
      >
        {/* Botón de Cierre */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
          title="Cerrar modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Encabezado del Modal (Stitch) */}
        <div className="border-b border-slate-100 pb-4 mb-5 pr-8">
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-blue-50 text-[#213F8B] border border-blue-100">
              <FileDown className="w-4 h-4" />
            </div>
            <h2 className="text-base font-extrabold text-[#213F8B] tracking-tight uppercase">
              EXPORTAR REPORTE DE AUDITORÍA
            </h2>
          </div>
          <p className="text-xs text-[#555555] ml-8">
            Generación y despacho oficial de dictamen técnico
          </p>
        </div>

        {/* Recibo de Éxito si ya se envió */}
        {successReceipt ? (
          <div className="space-y-4 animate-in fade-in">
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs space-y-2.5">
              <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <span>{successReceipt.message}</span>
              </div>
              <p className="text-[11px] text-emerald-700">
                Se ha generado el documento formal en PDF (Estándar INACAP) y se registró el despacho oficial al correo: <strong className="font-mono text-emerald-900">{successReceipt.recipient}</strong>.
              </p>
              <div className="pt-2 border-t border-emerald-200 grid grid-cols-2 gap-2 text-[11px] text-emerald-900">
                <div>
                  <span className="text-emerald-700 block">Folio de Despacho:</span>
                  <span className="font-mono font-bold text-emerald-950">{successReceipt.dispatch_id}</span>
                </div>
                <div>
                  <span className="text-emerald-700 block">Fecha y Hora UTC:</span>
                  <span className="font-mono font-medium">{successReceipt.timestamp_utc}</span>
                </div>
              </div>
              <div className="pt-2 text-[11px] text-emerald-800">
                <span className="text-emerald-700 block">Firma Criptográfica SHA-256 (Validez Probatoria):</span>
                <span className="font-mono text-[10px] break-all bg-white/80 p-1.5 rounded border border-emerald-200 block mt-0.5 select-all">
                  {successReceipt.integrity_signature}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={triggerDirectPdfDownload}
                className="px-3.5 py-2 bg-blue-50 hover:bg-blue-100 text-[#213F8B] border border-blue-200 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Descargar PDF nuevamente</span>
              </button>

              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2 bg-[#213F8B] hover:bg-[#1a326f] text-white rounded-lg text-xs font-semibold transition cursor-pointer"
              >
                Aceptar y Finalizar
              </button>
            </div>
          </div>
        ) : (
          /* Formulario de Exportación (Stitch) */
          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            {/* Metadatos de la Evaluación en Tarjeta */}
            <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200 space-y-2.5">
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Control evaluado:</span>
                <span className="font-semibold text-slate-800 text-right">{control}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Repositorio:</span>
                <span className="font-mono text-slate-700 text-right">{repository}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Veredicto:</span>
                <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${getVerdictStyle()}`}>
                  {verdict}
                </span>
              </div>

              <div className="pt-1 border-t border-slate-200">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-slate-500 font-medium">Hash de Integridad:</span>
                  <button
                    type="button"
                    onClick={handleCopyHash}
                    className="inline-flex items-center gap-1 text-[11px] text-[#213F8B] hover:underline cursor-pointer"
                  >
                    {copiedHash ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedHash ? 'Copiado' : 'Copiar'}</span>
                  </button>
                </div>
                <p className="font-mono text-[10px] text-slate-600 bg-white p-2 rounded border border-slate-200 break-all select-all">
                  {integrityHash}
                </p>
              </div>
            </div>

            {/* Checkbox: Formato PDF INACAP */}
            <div className="p-3 bg-white rounded-lg border border-slate-200 hover:border-slate-300 transition">
              <label className="flex items-start gap-2.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={generatePdf}
                  onChange={(e) => setGeneratePdf(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-[#213F8B] focus:ring-[#213F8B] cursor-pointer"
                />
                <div>
                  <span className="font-semibold text-slate-800 block">
                    Generar documento formal en formato PDF (Estándar INACAP)
                  </span>
                  <span className="text-[11px] text-slate-500">
                    Incluye plantilla oficial, membrete institucional y dictamen probatorio.
                  </span>
                </div>
              </label>
            </div>

            {/* Input: Enviar copia a correo del auditor */}
            <div>
              <label htmlFor="auditorEmail" className="block text-slate-700 font-semibold mb-1">
                Enviar copia a correo del auditor
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  id="auditorEmail"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="josemorahj23@gmail.com"
                  required
                  disabled={isLoading}
                  className="w-full pl-9 pr-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-xs font-mono text-slate-800 focus:outline-none focus:border-[#213F8B] transition"
                />
              </div>
            </div>

            {/* Nota de Seguridad Criptográfica */}
            <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-100 flex items-start gap-2.5 text-[11px] text-slate-600">
              <Lock className="w-4 h-4 text-[#213F8B] shrink-0 mt-0.5" />
              <span>
                El reporte incluye la firma criptográfica y marcas de tiempo UTC para validez probatoria.
              </span>
            </div>

            {/* Alerta de Error si ocurre */}
            {errorMessage && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 font-medium">
                {errorMessage}
              </div>
            )}

            {/* Botones de Acción */}
            <div className="pt-2 flex items-center justify-end gap-2.5 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                disabled={isLoading}
                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition cursor-pointer disabled:opacity-50"
              >
                Cancelar
              </button>

              <button
                type="submit"
                disabled={isLoading}
                className="px-5 py-2.5 bg-[#213F8B] hover:bg-[#1a326f] text-white rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Generando y Despachando...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Generar PDF y Enviar</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
