import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import LoginView from './views/LoginView';
import { isAuthenticated } from './api/client';
import { FileCheck2, Award, ArrowRight } from 'lucide-react';

export default function App() {
  const [currentStep, setCurrentStep] = useState('login');

  useEffect(() => {
    if (isAuthenticated()) {
      // If already authenticated, user can start at evaluacion or login
      setCurrentStep('evaluacion');
    } else {
      setCurrentStep('login');
    }
  }, []);

  const handleNavigate = (step) => {
    if ((step === 'evaluacion' || step === 'resultado') && !isAuthenticated()) {
      setCurrentStep('login');
      return;
    }
    setCurrentStep(step);
  };

  const handleLoginSuccess = () => {
    setCurrentStep('evaluacion');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-emerald-500 selection:text-slate-950">
      <Navbar currentStep={currentStep} onNavigate={handleNavigate} />

      <main className="flex-1">
        {currentStep === 'login' && (
          <LoginView onLoginSuccess={handleLoginSuccess} />
        )}

        {currentStep === 'evaluacion' && (
          <div className="max-w-4xl mx-auto p-6 sm:p-12 text-center animate-in fade-in duration-200">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-mono mb-4">
              Paso 2 / 3 · Pantalla E
            </div>
            <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center mx-auto mb-4">
              <FileCheck2 className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Pantalla de Evaluación (/evaluacion)</h2>
            <p className="text-slate-400 text-sm max-w-lg mx-auto mb-6">
              Esta pantalla se implementará en la siguiente rama <code className="text-cyan-300 font-mono">feature/frontend-evaluacion</code> para el control reactivo GH-001 y GH-002 con inyección oculta de GitHub Token.
            </p>
            <div className="flex justify-center gap-3">
              <button
                onClick={() => setCurrentStep('login')}
                className="px-4 py-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-xl text-xs font-medium text-slate-300 transition"
              >
                Volver al Login
              </button>
            </div>
          </div>
        )}

        {currentStep === 'resultado' && (
          <div className="max-w-4xl mx-auto p-6 sm:p-12 text-center animate-in fade-in duration-200">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono mb-4">
              Paso 3 / 3 · Pantalla R
            </div>
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto mb-4">
              <Award className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Pantalla de Resultado (/resultado)</h2>
            <p className="text-slate-400 text-sm max-w-lg mx-auto mb-6">
              Esta pantalla se implementará en la rama <code className="text-emerald-300 font-mono">feature/frontend-resultado</code> para mostrar la tarjeta criptográfica con hash SHA-256 inmutable y las 4 variantes de veredicto.
            </p>
            <div className="flex justify-center gap-3">
              <button
                onClick={() => setCurrentStep('evaluacion')}
                className="px-4 py-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-xl text-xs font-medium text-slate-300 transition"
              >
                Ir a Evaluación
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
