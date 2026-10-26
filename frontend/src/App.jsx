import React, { useState, useEffect } from 'react';
import LoginView from './views/LoginView';
import EvaluacionView from './views/EvaluacionView';
import { isAuthenticated, clearSession } from './api/client';
import { Award, ArrowLeft } from 'lucide-react';

export default function App() {
  const [currentStep, setCurrentStep] = useState('login');
  const [evaluationResult, setEvaluationResult] = useState(null);

  useEffect(() => {
    if (isAuthenticated()) {
      setCurrentStep('evaluacion');
    } else {
      setCurrentStep('login');
    }
  }, []);

  const handleLoginSuccess = () => {
    setCurrentStep('evaluacion');
  };

  const handleLogout = () => {
    clearSession();
    setEvaluationResult(null);
    setCurrentStep('login');
  };

  const handleEvaluationSuccess = (data, controlId) => {
    setEvaluationResult({ data, controlId });
    setCurrentStep('resultado');
  };

  return (
    <div className="min-h-screen bg-[#F4F6FA] text-slate-800 flex flex-col font-sans">
      {/* 1. Paso L: Login */}
      {currentStep === 'login' && (
        <LoginView onLoginSuccess={handleLoginSuccess} />
      )}

      {/* 2. Paso E: Evaluación */}
      {currentStep === 'evaluacion' && (
        <EvaluacionView 
          onLogout={handleLogout} 
          onEvaluationSuccess={handleEvaluationSuccess} 
        />
      )}

      {/* 3. Paso R: Resultado (Placeholder para la siguiente rama feature/frontend-resultado) */}
      {currentStep === 'resultado' && (
        <div className="min-h-screen w-full flex flex-col font-sans" style={{ backgroundColor: '#F4F6FA' }}>
          <header className="w-full bg-white border-b border-slate-200">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="font-extrabold text-lg tracking-wide" style={{ color: '#213F8B' }}>
                  SECURECODE
                </span>
                <span className="text-slate-300">|</span>
                <span className="text-sm font-medium text-slate-700">
                  Resultado de Evaluación
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

          <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
            <div 
              className="w-full max-w-[500px] bg-white border border-slate-200 shadow-md p-6 sm:p-8 text-center"
              style={{ borderRadius: '8px' }}
            >
              <div 
                className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4"
                style={{ backgroundColor: '#F4F6FA', color: '#213F8B' }}
              >
                <Award className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold mb-2" style={{ color: '#213F8B' }}>
                Evaluación Completada
              </h2>
              <p className="text-xs mb-6" style={{ color: '#555555' }}>
                Datos recibidos para control <strong>{evaluationResult?.controlId || 'GH-001'}</strong>. Esta pantalla se implementará en la rama <code className="bg-slate-100 px-1 py-0.5 rounded font-mono">feature/frontend-resultado</code> (Fórmula 3-4-2 Paso 3).
              </p>
              <button
                onClick={() => setCurrentStep('evaluacion')}
                className="px-4 py-2 text-xs font-medium rounded transition hover:bg-slate-100 border border-slate-300 flex items-center gap-2 mx-auto cursor-pointer"
                style={{ color: '#555555' }}
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Volver a Evaluación</span>
              </button>
            </div>
          </main>
        </div>
      )}
    </div>
  );
}
