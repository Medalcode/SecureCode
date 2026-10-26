import React from 'react';
import { ShieldCheck, LogOut, Lock, FileCheck2, Award } from 'lucide-react';
import { clearSession, isAuthenticated, getStoredUser } from '../api/client';

export default function Navbar({ currentStep = 'login', onNavigate }) {
  const logged = isAuthenticated();
  const username = getStoredUser();

  const handleLogout = () => {
    clearSession();
    if (onNavigate) {
      onNavigate('login');
    }
  };

  const steps = [
    { id: 'login', label: '1. Login (L)', icon: Lock, path: '/login' },
    { id: 'evaluacion', label: '2. Evaluación (E)', icon: FileCheck2, path: '/evaluacion', disabled: !logged },
    { id: 'resultado', label: '3. Resultado (R)', icon: Award, path: '/resultado', disabled: !logged },
  ];

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-[#0f2744]">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base text-[#0f2744] tracking-wider">SECURECODE</span>
              <span className="text-[11px] px-2 py-0.5 rounded font-medium bg-slate-100 text-slate-600 border border-slate-200">
                Flujo L.E.R.
              </span>
            </div>
            <p className="text-[11px] text-slate-500">Evaluación automatizada de controles</p>
          </div>
        </div>

        {/* Steps indicator */}
        <nav className="hidden md:flex items-center gap-1 bg-slate-50 p-1 rounded-xl border border-slate-200">
          {steps.map((step) => {
            const Icon = step.icon;
            const isActive = currentStep === step.id;
            return (
              <button
                key={step.id}
                disabled={step.disabled}
                onClick={() => onNavigate && onNavigate(step.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-white text-[#0f2744] border border-slate-200 shadow-sm font-semibold'
                    : step.disabled
                    ? 'text-slate-400 cursor-not-allowed'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{step.label}</span>
              </button>
            );
          })}
        </nav>

        {/* User Info / Logout */}
        <div className="flex items-center gap-3">
          {logged ? (
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <p className="text-xs font-semibold text-slate-800">{username}</p>
                <p className="text-[10px] text-emerald-600 font-mono font-medium">Sesión Activa (JWT)</p>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-700 bg-red-50 border border-red-200 hover:bg-red-100 rounded-lg transition cursor-pointer"
                title="Cerrar sesión"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Salir</span>
              </button>
            </div>
          ) : (
            <span className="text-xs text-slate-500">Sin autenticar</span>
          )}
        </div>
      </div>
    </header>
  );
}
