import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  CreditCard, 
  Calendar, 
  CheckCircle2, 
  FileText, 
  Download, 
  ShieldCheck, 
  HardDrive, 
  Clock, 
  Headphones, 
  RotateCw, 
  ExternalLink,
  Lock,
  Layers,
  FileCheck,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import Navbar from '../components/Navbar';
import { fetchBillingSummary } from '../api/client';

const FALLBACK_BILLING = {
  app: "SECURECODE",
  navigation: "Centro de Control y Suscripción",
  title: "Centro de Control y Facturación",
  subtitle: "Gestión de licencia corporativa, límites de auditoría y facturación electrónica.",
  environment: "Entorno Enterprise",
  subscription_plan: {
    status: "PLAN DE SUSCRIPCIÓN ACTIVO",
    plan_name: "Plan Piloto Institucional",
    badge: "ACTIVO / AL DÍA",
    description: "Monitoreo continuo de código fuente y cumplimiento normativo ISO/IEC 27001.",
    price: "$150.000 CLP / mes",
    next_billing_date: "01 de Noviembre, 2026",
    billing_modality: {
      title: "Modalidad de Facturación",
      description: "Transferencia bancaria / Facturación electrónica",
      company_rut: "76.842.109-K"
    },
    corporate_assistance: {
      title: "Asistencia Corporativa",
      description: "Ejecutivo de cuentas asignado",
      action: "Gestionar"
    }
  },
  monthly_usage: {
    title: "CONSUMO DE EVALUACIONES MENSUALES",
    cycle: "CICLO OCT 2026",
    description: "Capacidad asignada para pipelines CI/CD y análisis estático SAST.",
    consumed: 38,
    max: 500,
    usage_percentage: "7.6% de uso",
    available_evaluations: 462,
    storage: {
      title: "Capacidad de almacenamiento de reportes",
      used: "1.2 MB de 500 MB (Cuota de base de datos)",
      retention_policy: "Los artefactos y trazas de auditoría se conservan cifrados en reposo durante 365 días bajo cumplimiento de retención.",
      percentage: "0.2%"
    }
  },
  billing_history: {
    title: "HISTORIAL DE FACTURACIÓN",
    subtitle: "Registro de pagos y facturas tributarias emitidas",
    columns: ["FECHA", "CONCEPTO", "MONTO", "ESTADO", "COMPROBANTE"],
    rows: [
      {
        date: "01/10/2026",
        concept: "Mensualidad SecureCode Octubre",
        reference: "INV-2026-10-8841",
        amount: "$150.000 CLP",
        status: "Pagado",
        invoice_action: "Descargar Factura"
      },
      {
        date: "01/09/2026",
        concept: "Mensualidad SecureCode Septiembre",
        reference: "INV-2026-09-7612",
        amount: "$150.000 CLP",
        status: "Pagado",
        invoice_action: "Descargar Factura"
      }
    ],
    footer_note: "Mostrando los últimos 2 comprobantes tributarios electrónicos (DTE).",
    link: "Solicitar histórico de auditoría contable"
  },
  footer: {
    platform: "SECURECODE Cybersecurity Platform",
    sla: "SLA Enterprise 99.9%",
    security: "Conexión Segura TLS 1.3",
    audit_id: "ID Auditoría: SEC-BLL-2026"
  }
};

export default function BillingView({ onLogout, onNavigate }) {
  const [billingData, setBillingData] = useState(FALLBACK_BILLING);
  const [loading, setLoading] = useState(true);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [assistanceModal, setAssistanceModal] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await fetchBillingSummary();
      if (res.success && res.data) {
        setBillingData(res.data);
      }
    } catch (e) {
      console.warn("Using fallback billing data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const { subscription_plan, monthly_usage, billing_history, footer } = billingData;
  const consumed = monthly_usage?.consumed || 38;
  const max = monthly_usage?.max || 500;
  const percentNum = ((consumed / max) * 100).toFixed(1);

  return (
    <div className="min-h-screen bg-[#F4F6FA] flex flex-col font-sans">
      <Navbar currentStep="facturacion" onNavigate={onNavigate} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        
        {/* Encabezado Principal */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold tracking-wider text-slate-500 uppercase">
                {billingData.navigation || 'Centro de Control y Suscripción'}
              </span>
              <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-blue-100 text-[#213F8B] border border-blue-200 rounded-md">
                {billingData.environment || 'Entorno Enterprise'}
              </span>
            </div>
            <h1 className="text-2xl font-black text-[#213F8B] tracking-tight">
              {billingData.title || 'Centro de Control y Facturación'}
            </h1>
            <p className="text-xs text-[#555555] mt-0.5">
              {billingData.subtitle || 'Gestión de licencia corporativa, límites de auditoría y facturación electrónica.'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              className="p-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-xs font-medium flex items-center gap-1.5 transition shadow-sm cursor-pointer"
              title="Refrescar estado de suscripción"
            >
              <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin text-[#213F8B]' : ''}`} />
              <span className="hidden sm:inline">Actualizar</span>
            </button>
          </div>
        </div>

        {/* 1. Tarjeta de Suscripción Principal (Stitch Card) */}
        <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6 relative overflow-hidden">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  {subscription_plan?.status || 'PLAN DE SUSCRIPCIÓN ACTIVO'}
                </span>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#EBF7EE] text-[#1E7E34] border border-[#C3E6CB]">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {subscription_plan?.badge || 'ACTIVO / AL DÍA'}
                </span>
              </div>
              <h2 className="text-2xl font-black text-slate-900">
                {subscription_plan?.plan_name || 'Plan Piloto Institucional'}
              </h2>
              <p className="text-xs text-slate-600 mt-1 max-w-xl">
                {subscription_plan?.description || 'Monitoreo continuo de código fuente y cumplimiento normativo ISO/IEC 27001.'}
              </p>
            </div>

            <div className="lg:text-right bg-slate-50 lg:bg-transparent p-4 lg:p-0 rounded-lg border lg:border-none border-slate-200">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Tarifa mensual</span>
              <span className="text-2xl font-black text-[#213F8B]">
                {subscription_plan?.price || '$150.000 CLP / mes'}
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Próximo ciclo: <span className="font-semibold text-slate-700">{subscription_plan?.next_billing_date || '01 de Noviembre, 2026'}</span>
              </p>
            </div>
          </div>

          {/* Sub-paneles: Modalidad y Asistencia */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-white border border-slate-200 text-[#213F8B] shadow-2xs">
                <CreditCard className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-800">
                  {subscription_plan?.billing_modality?.title || 'Modalidad de Facturación'}
                </h4>
                <p className="text-xs text-slate-600 mt-0.5">
                  {subscription_plan?.billing_modality?.description || 'Transferencia bancaria / Facturación electrónica'}
                </p>
                <p className="text-[11px] font-mono font-semibold text-slate-500 mt-1">
                  RUT Empresa: {subscription_plan?.billing_modality?.company_rut || '76.842.109-K'}
                </p>
              </div>
            </div>

            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-white border border-slate-200 text-[#213F8B] shadow-2xs">
                  <Headphones className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-800">
                    {subscription_plan?.corporate_assistance?.title || 'Asistencia Corporativa'}
                  </h4>
                  <p className="text-xs text-slate-600 mt-0.5">
                    {subscription_plan?.corporate_assistance?.description || 'Ejecutivo de cuentas asignado'}
                  </p>
                  <p className="text-[11px] text-emerald-700 font-semibold mt-1">
                    Soporte Prioritario 24/7
                  </p>
                </div>
              </div>
              <button
                onClick={() => setAssistanceModal(true)}
                className="px-3 py-1.5 text-xs font-semibold bg-white hover:bg-slate-100 text-[#213F8B] border border-slate-300 rounded-md transition shadow-2xs cursor-pointer"
              >
                {subscription_plan?.corporate_assistance?.action || 'Gestionar'}
              </button>
            </div>
          </div>
        </div>

        {/* 2. Sección: Consumo de Evaluaciones Mensuales */}
        <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-[#213F8B] tracking-wide uppercase">
                  {monthly_usage?.title || 'CONSUMO DE EVALUACIONES MENSUALES'}
                </h3>
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-slate-100 text-slate-700 rounded border border-slate-200">
                  {monthly_usage?.cycle || 'CICLO OCT 2026'}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {monthly_usage?.description || 'Capacidad asignada para pipelines CI/CD y análisis estático SAST.'}
              </p>
            </div>
            <div className="text-right">
              <span className="text-xs font-bold text-slate-800">
                {consumed} / {max}
              </span>
              <span className="text-xs text-slate-500 ml-1">
                ({monthly_usage?.usage_percentage || `${percentNum}% de uso`})
              </span>
            </div>
          </div>

          {/* Barra de Progreso Stitch */}
          <div className="w-full bg-slate-100 rounded-full h-3.5 border border-slate-200 p-0.5 mb-4">
            <div 
              className="bg-[#213F8B] h-full rounded-full transition-all duration-500 ease-out"
              style={{ width: `${Math.min(100, Math.max(3, percentNum))}%` }}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-3 border-t border-slate-100 text-xs">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-500 block text-[11px]">Evaluaciones consumidas</span>
              <span className="text-lg font-black text-slate-900 mt-0.5 block">{consumed}</span>
              <span className="text-[10px] text-slate-400">Verificadas en PostgreSQL</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-500 block text-[11px]">Cuota disponible</span>
              <span className="text-lg font-black text-emerald-700 mt-0.5 block">
                {monthly_usage?.available_evaluations ?? (max - consumed)}
              </span>
              <span className="text-[10px] text-slate-400">Disponibles hasta fin de ciclo</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-500 block text-[11px]">Límite por contrato</span>
              <span className="text-lg font-black text-slate-900 mt-0.5 block">{max} evals/mes</span>
              <span className="text-[10px] text-slate-400">Renovación mensual automática</span>
            </div>
          </div>

          {/* Tarjeta de Almacenamiento */}
          <div className="mt-5 p-4 rounded-lg bg-blue-50/50 border border-blue-100 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-white border border-blue-200 text-[#213F8B]">
                <HardDrive className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-bold text-slate-900">
                    {monthly_usage?.storage?.title || 'Capacidad de almacenamiento de reportes'}
                  </h4>
                  <span className="px-1.5 py-0.5 text-[10px] font-mono bg-blue-100 text-[#213F8B] rounded font-bold">
                    {monthly_usage?.storage?.percentage || '0.2%'}
                  </span>
                </div>
                <p className="text-slate-600 font-medium mt-0.5">
                  {monthly_usage?.storage?.used || '1.2 MB de 500 MB (Cuota de base de datos)'}
                </p>
                <p className="text-[11px] text-slate-500 mt-1">
                  {monthly_usage?.storage?.retention_policy || 'Los artefactos y trazas de auditoría se conservan cifrados en reposo durante 365 días bajo cumplimiento de retención.'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* 3. Sección: Historial de Facturación (Stitch Table) */}
        <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
          <div className="p-5 border-b border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-bold text-[#213F8B] uppercase tracking-wide">
                {billing_history?.title || 'HISTORIAL DE FACTURACIÓN'}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {billing_history?.subtitle || 'Registro de pagos y facturas tributarias emitidas'}
              </p>
            </div>
            <span className="text-xs text-slate-400 font-medium">
              Moneda: Peso Chileno (CLP)
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">FECHA</th>
                  <th className="py-3 px-4">CONCEPTO</th>
                  <th className="py-3 px-4">MONTO</th>
                  <th className="py-3 px-4">ESTADO</th>
                  <th className="py-3 px-4 text-right">COMPROBANTE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-normal text-slate-700">
                {(billing_history?.rows || []).map((row, idx) => (
                  <tr key={row.reference || idx} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 whitespace-nowrap font-medium text-slate-800">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{row.date}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div>
                        <span className="font-semibold text-slate-800 block">{row.concept}</span>
                        <span className="font-mono text-[11px] text-slate-400">{row.reference}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-900 whitespace-nowrap">
                      {row.amount}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#EBF7EE] text-[#1E7E34] border border-[#C3E6CB]">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {row.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => setSelectedInvoice(row)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#213F8B] bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>{row.invoice_action || 'Descargar Factura'}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="py-3 px-5 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500 font-medium">
            <span>
              {billing_history?.footer_note || 'Mostrando los últimos 2 comprobantes tributarios electrónicos (DTE).'}
            </span>
            <button
              onClick={() => alert("Historial contable completo solicitado. Se enviará copia firmada al correo del administrador.")}
              className="text-[#213F8B] hover:underline font-semibold cursor-pointer"
            >
              {billing_history?.link || 'Solicitar histórico de auditoría contable'} →
            </button>
          </div>
        </div>

        {/* 4. Footer Institucional Stitch */}
        <div className="py-6 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#213F8B]" />
            <span className="font-semibold text-slate-700">{footer?.platform || 'SECURECODE Cybersecurity Platform'}</span>
            <span className="text-slate-300">|</span>
            <span>{footer?.sla || 'SLA Enterprise 99.9%'}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1 text-slate-600 font-mono text-[11px]">
              <Lock className="w-3 h-3 text-emerald-600" />
              {footer?.security || 'Conexión Segura TLS 1.3'}
            </span>
            <span className="text-slate-300">|</span>
            <span className="font-mono text-[11px] text-slate-400">
              {footer?.audit_id || 'ID Auditoría: SEC-BLL-2026'}
            </span>
          </div>
        </div>

      </main>

      {/* Modal Factura Electrónica DTE */}
      {selectedInvoice && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-[#213F8B]" />
                <h3 className="font-bold text-base text-slate-800">Comprobante Fiscal Digital (DTE)</h3>
              </div>
              <button
                onClick={() => setSelectedInvoice(null)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">Folio Tributario:</span>
                  <span className="font-mono font-bold text-slate-800">{selectedInvoice.reference}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Fecha de Emisión:</span>
                  <span className="text-slate-800 font-medium">{selectedInvoice.date}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Concepto:</span>
                  <span className="text-slate-800 font-medium">{selectedInvoice.concept}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Facturado:</span>
                  <span className="font-mono font-bold text-slate-900">{selectedInvoice.amount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Estado de Pago:</span>
                  <span className="text-emerald-700 font-bold">{selectedInvoice.status} (Conciliado)</span>
                </div>
              </div>

              <p className="text-[11px] text-slate-400 text-center">
                Documento Tributario Electrónico timbrado y firmado digitalmente según normativa del Servicio de Impuestos Internos.
              </p>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => setSelectedInvoice(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition cursor-pointer"
              >
                Cerrar
              </button>
              <button
                onClick={() => {
                  alert(`Descarga iniciada para el comprobante ${selectedInvoice.reference}.pdf`);
                  setSelectedInvoice(null);
                }}
                className="px-4 py-2 bg-[#213F8B] hover:bg-[#1a326f] text-white rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                Descargar PDF
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Asistencia Corporativa */}
      {assistanceModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <Headphones className="w-5 h-5 text-[#213F8B]" />
                <h3 className="font-bold text-base text-slate-800">Ejecutivo de Cuentas Enterprise</h3>
              </div>
              <button
                onClick={() => setAssistanceModal(false)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-2">
                <div>
                  <span className="text-[11px] text-slate-400 block">Ejecutivo Asignado:</span>
                  <span className="font-semibold text-slate-800">Rodrigo Sepúlveda — Cuentas Corporativas</span>
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 block">Correo Institucional:</span>
                  <span className="font-mono text-slate-800">soporte.enterprise@securecode.inacap.cl</span>
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 block">Teléfono Directo:</span>
                  <span className="font-mono text-slate-800">+56 2 2940 1800</span>
                </div>
              </div>
              <p className="text-[11px] text-slate-500">
                Tu plan incluye SLA de respuesta menor a 2 horas para incidentes de auditoría y facturación.
              </p>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setAssistanceModal(false)}
                className="px-4 py-2 bg-[#213F8B] text-white rounded-lg text-xs font-semibold transition cursor-pointer"
              >
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

