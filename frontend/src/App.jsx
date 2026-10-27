import React, { useState, useEffect } from 'react';
import LoginView from './views/LoginView';
import EvaluacionView from './views/EvaluacionView';
import ResultadoView from './views/ResultadoView';
import HistorialView from './views/HistorialView';
import { isAuthenticated, clearSession } from './api/client';

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

  const handleNewEvaluation = () => {
    setCurrentStep('evaluacion');
  };

  const handleNavigate = (step) => {
    setCurrentStep(step);
  };

  return (
    <div className="min-h-screen bg-[#F4F6FA] text-slate-800 flex flex-col font-sans">
      {/* 1. Paso L: Login (/login) */}
      {currentStep === 'login' && (
        <LoginView onLoginSuccess={handleLoginSuccess} />
      )}

      {/* 2. Paso E: Evaluación (/evaluacion) */}
      {currentStep === 'evaluacion' && (
        <EvaluacionView 
          onLogout={handleLogout} 
          onEvaluationSuccess={handleEvaluationSuccess} 
          onNavigate={handleNavigate}
        />
      )}

      {/* 3. Paso R: Resultado (/resultado) con las 4 Variantes */}
      {currentStep === 'resultado' && (
        <ResultadoView
          resultData={evaluationResult?.data}
          controlId={evaluationResult?.controlId || 'GH-001'}
          onLogout={handleLogout}
          onNewEvaluation={handleNewEvaluation}
          onNavigate={handleNavigate}
        />
      )}

      {/* 4. Fase 2: Historial de Ejecuciones (/historial) */}
      {currentStep === 'historial' && (
        <HistorialView
          onLogout={handleLogout}
          onNewEvaluation={handleNewEvaluation}
          onNavigate={handleNavigate}
        />
      )}
    </div>
  );
}
