import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import LoginView from './views/LoginView';
import { isAuthenticated } from './api/client';
import { FileCheck2, Award } from 'lucide-react';

export default function App() {
  const [currentStep, setCurrentStep] = useState('login');

  useEffect(() => {
    if (isAuthenticated()) {
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
    <div className="min-h-screen bg-[#F4F6FA] text-slate-800 flex flex-col font-sans">
      {/* En la pantalla de login mostramos el formulario centrado puro del mockup */}
      {currentStep === 'login' ? (
        <LoginView onLoginSuccess={handleLoginSuccess} />
      ) : (
        <>
          <Navbar currentStep={currentStep} onNavigate={handleNavigate} />
          <main className="flex-1 max-w-5xl mx-auto w-full p-6 sm:p-10">
            {currentStep === 'evaluacion' && (
              <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm text-center">
                <div className="w-14 h-14 rounded-2xl bg-slate-100 border border-slate-200 text-[#0f2744] flex items-center justify-center mx-auto mb-4">
                  <FileCheck2 className="w-7 h-7" />
                </div>
                <h2 className="text-xl font-bold text-[#0f2744] mb-2">Pantalla de Evaluación (/evaluacion)</h2>
                <p className="text-slate-500 text-sm max-w-lg mx-auto mb-6">
                  Preparada para la rama <code className="bg-slate-100 px-2 py-0.5 rounded text-slate-700 font-mono text-xs">feature/frontend-evaluacion</code>.
                </p>
                <button
                  onClick={() => setCurrentStep('login')}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition cursor-pointer"
                >
                  Volver al Login
                </button>
              </div>
            )}

            {currentStep === 'resultado' && (
              <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm text-center">
                <div className="w-14 h-14 rounded-2xl bg-slate-100 border border-slate-200 text-[#0f2744] flex items-center justify-center mx-auto mb-4">
                  <Award className="w-7 h-7" />
                </div>
                <h2 className="text-xl font-bold text-[#0f2744] mb-2">Pantalla de Resultado (/resultado)</h2>
                <p className="text-slate-500 text-sm max-w-lg mx-auto mb-6">
                  Preparada para la rama <code className="bg-slate-100 px-2 py-0.5 rounded text-slate-700 font-mono text-xs">feature/frontend-resultado</code>.
                </p>
                <button
                  onClick={() => setCurrentStep('evaluacion')}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition cursor-pointer"
                >
                  Ir a Evaluación
                </button>
              </div>
            )}
          </main>
        </>
      )}
    </div>
  );
}
