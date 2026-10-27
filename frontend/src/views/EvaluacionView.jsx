import React, { useState } from 'react';
import { clearSession, evaluateControl } from '../api/client';
import { AlertCircle, Loader2 } from 'lucide-react';
import Navbar from '../components/Navbar';

export default function EvaluacionView({ onLogout, onEvaluationSuccess, onNavigate }) {
  const [activeTab, setActiveTab] = useState('GH-001'); // 'GH-001' | 'GH-002'

  // Estados del formulario
  const [owner, setOwner] = useState('acme-corp');
  const [repository, setRepository] = useState('payment-gateway');
  const [branch, setBranch] = useState('main');

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleLogout = () => {
    clearSession();
    if (onLogout) {
      onLogout();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    if (!owner.trim() || !repository.trim()) {
      setErrorMessage('Por favor ingrese Propietario y Repositorio.');
      return;
    }

    if (activeTab === 'GH-001' && !branch.trim()) {
      setErrorMessage('Por favor ingrese la Rama a evaluar.');
      return;
    }

    setIsLoading(true);

    const payload = activeTab === 'GH-001' 
      ? { owner: owner.trim(), repository: repository.trim(), branch: branch.trim() }
      : { owner: owner.trim(), repository: repository.trim() };

    const result = await evaluateControl(activeTab, payload);

    setIsLoading(false);

    if (!result.success) {
      if (result.status >= 500 || result.status === 0) {
        if (onEvaluationSuccess) {
          onEvaluationSuccess({
            isError: true,
            message: 'Servicio no disponible. No se registró ninguna evaluación. Intente nuevamente más tarde.',
          }, activeTab);
        }
      } else {
        setErrorMessage(result.message);
      }
    } else {
      if (onEvaluationSuccess) {
        onEvaluationSuccess(result.data, activeTab);
      }
    }
  };

  return (
    <div 
      className="min-h-screen w-full flex flex-col font-sans"
      style={{ backgroundColor: '#F4F6FA' }}
    >
      {/* Barra de Navegación Unificada Stitch */}
      <Navbar currentStep="evaluacion" onNavigate={onNavigate} />

      {/* Contenedor Principal */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
        <div 
          className="w-full max-w-[480px] bg-white border border-slate-200 shadow-md p-6 sm:p-8"
          style={{ borderRadius: '8px' }}
        >
          {/* Pestañas (Tabs) */}
          <div className="flex border-b border-slate-200 mb-6">
            <button
              type="button"
              onClick={() => {
                setActiveTab('GH-001');
                setErrorMessage('');
              }}
              className="flex-1 py-2.5 text-xs sm:text-sm font-semibold transition border-b-2 text-center cursor-pointer"
              style={{
                color: activeTab === 'GH-001' ? '#213F8B' : '#555555',
                borderColor: activeTab === 'GH-001' ? '#213F8B' : 'transparent',
              }}
            >
              GH-001 Revisión por pares
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab('GH-002');
                setErrorMessage('');
              }}
              className="flex-1 py-2.5 text-xs sm:text-sm font-semibold transition border-b-2 text-center cursor-pointer"
              style={{
                color: activeTab === 'GH-002' ? '#213F8B' : '#555555',
                borderColor: activeTab === 'GH-002' ? '#213F8B' : 'transparent',
              }}
            >
              GH-002 Protección de rama
            </button>
          </div>

          {/* Formulario */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Campo: Propietario (owner) */}
            <div>
              <label 
                htmlFor="owner" 
                className="block text-xs font-medium mb-1.5"
                style={{ color: '#555555' }}
              >
                Propietario (owner)
              </label>
              <input
                id="owner"
                type="text"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                placeholder="acme-corp"
                disabled={isLoading}
                required
                className="w-full px-3.5 py-2.5 bg-white border border-slate-300 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#213F8B] transition disabled:bg-slate-50"
                style={{ borderRadius: '8px' }}
              />
            </div>

            {/* Campo: Repositorio */}
            <div>
              <label 
                htmlFor="repository" 
                className="block text-xs font-medium mb-1.5"
                style={{ color: '#555555' }}
              >
                Repositorio
              </label>
              <input
                id="repository"
                type="text"
                value={repository}
                onChange={(e) => setRepository(e.target.value)}
                placeholder="payment-gateway"
                disabled={isLoading}
                required
                className="w-full px-3.5 py-2.5 bg-white border border-slate-300 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#213F8B] transition disabled:bg-slate-50"
                style={{ borderRadius: '8px' }}
              />
            </div>

            {/* Campo: Rama (branch) - Solo para GH-001 */}
            {activeTab === 'GH-001' && (
              <div>
                <label 
                  htmlFor="branch" 
                  className="block text-xs font-medium mb-1.5"
                  style={{ color: '#555555' }}
                >
                  Rama (branch)
                </label>
                <input
                  id="branch"
                  type="text"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="main"
                  disabled={isLoading}
                  required
                  className="w-full px-3.5 py-2.5 bg-white border border-slate-300 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#213F8B] transition disabled:bg-slate-50"
                  style={{ borderRadius: '8px' }}
                />
              </div>
            )}

            {/* Botón: Evaluar */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 px-4 font-semibold text-sm transition shadow-sm hover:opacity-95 active:opacity-90 disabled:opacity-60 cursor-pointer flex items-center justify-center gap-2"
                style={{
                  backgroundColor: '#213F8B',
                  color: '#FFFFFF',
                  borderRadius: '8px',
                }}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Evaluando...</span>
                  </>
                ) : (
                  'Evaluar'
                )}
              </button>
            </div>
          </form>

          {/* Alerta de Error si ocurre */}
          {errorMessage && (
            <div 
              className="mt-4 p-3 flex items-center gap-2.5 text-xs animate-in fade-in duration-150"
              style={{
                backgroundColor: '#FDF2F2',
                border: '1px solid #F5C6CB',
                borderRadius: '8px',
                color: '#C0392B',
              }}
            >
              <AlertCircle className="w-4 h-4 shrink-0" style={{ color: '#C0392B' }} />
              <span className="font-medium">{errorMessage}</span>
            </div>
          )}

          {/* Nota al pie */}
          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>La evaluación es de solo lectura.</span>
            <button
              type="button"
              onClick={() => onNavigate && onNavigate('historial')}
              className="text-[#213F8B] hover:underline font-medium cursor-pointer"
            >
              Ver historial de evaluaciones →
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
