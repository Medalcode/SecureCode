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
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-sm shadow-emerald-500/10">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-slate-100 tracking-tight">SecureCode</span>
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-cyan-950/80 text-cyan-400 border border-cyan-800/60">
                Flujo L.E.R.
              </span>
            </div>
            <p className="text-xs text-slate-400">Auditoría Criptográfica SCM · INACAP</p>
          </div>
        </div>

        {/* Steps indicator */}
        <nav className="hidden md:flex items-center gap-1 bg-slate-900/90 p-1 rounded-xl border border-slate-800">
          {steps.map((step) => {
            const Icon = step.icon;
            const isActive = currentStep === step.id;
            return (
              <button
                key={step.id}
                disabled={step.disabled}
                onClick={() => onNavigate && onNavigate(step.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                    : step.disabled
                    ? 'text-slate-600 cursor-not-allowed'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
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
                <p className="text-xs font-semibold text-slate-200">{username}</p>
                <p className="text-[10px] text-emerald-400 font-mono">JWT HS256 ACTIVO</p>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-rose-300 bg-rose-950/30 border border-rose-800/40 hover:bg-rose-900/40 rounded-lg transition"
                title="Cerrar sesión"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Salir</span>
              </button>
            </div>
          ) : (
            <span className="text-xs text-slate-500 font-mono flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-400 inline-block animate-pulse"></span>
              Sesión requerida
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
