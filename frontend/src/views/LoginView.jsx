import React, { useState } from 'react';
import { 
  Lock, 
  User, 
  KeyRound, 
  Eye, 
  EyeOff, 
  AlertCircle, 
  CheckCircle2, 
  Loader2, 
  ShieldCheck,
  Cpu,
  Layers
} from 'lucide-react';
import { loginUser } from '../api/client';

export default function LoginView({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successNotice, setSuccessNotice] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessNotice(false);

    if (!username.trim() || !password) {
      setErrorMessage('Por favor ingrese usuario y contraseña.');
      return;
    }

    setIsLoading(true);

    const result = await loginUser(username, password);

    setIsLoading(false);

    if (!result.success) {
      setErrorMessage(result.message);
    } else {
      setSuccessNotice(true);
      setTimeout(() => {
        if (onLoginSuccess) {
          onLoginSuccess(result.data);
        }
      }, 600);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      <div className="w-full max-w-md">
        {/* Header Badge */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Fórmula 3-4-2 · Paso 1 / 3
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Acceso de Auditor
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Pantalla <strong className="text-emerald-400">L</strong> del Flujo L.E.R. · OAuth2 Bearer Token
          </p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/60 backdrop-blur-sm">
          {/* Alerta de Error Contextual */}
          {errorMessage && (
            <div className="mb-5 p-3.5 rounded-xl bg-rose-950/60 border border-rose-600/50 text-rose-200 text-xs flex items-start gap-3 animate-in fade-in duration-200">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-rose-300">Autenticación Rechazada</p>
                <p className="mt-0.5 text-rose-200/90 leading-relaxed">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* Notificación de Éxito */}
          {successNotice && (
            <div className="mb-5 p-3.5 rounded-xl bg-emerald-950/60 border border-emerald-500/50 text-emerald-200 text-xs flex items-center gap-3 animate-in fade-in duration-200">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <div>
                <p className="font-semibold text-emerald-300">Token JWT Emitido (HS256)</p>
                <p className="text-emerald-200/80">Redirigiendo a Evaluación (Pantalla E)...</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Campo Usuario */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 tracking-wide uppercase">
                Usuario Auditor
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="ej. auditor@securecode"
                  disabled={isLoading}
                  autoComplete="username"
                  required
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 transition disabled:opacity-50"
                />
              </div>
            </div>

            {/* Campo Contraseña */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 tracking-wide uppercase">
                Contraseña Criptográfica
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <KeyRound className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  disabled={isLoading}
                  autoComplete="current-password"
                  required
                  className="w-full pl-9 pr-10 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 focus:border-emerald-500 transition disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300 transition"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Botón de Envío */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold rounded-xl text-sm shadow-lg shadow-emerald-950/50 hover:shadow-emerald-900/30 transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Verificando credenciales con Argon2id...</span>
                  </>
                ) : (
                  <>
                    <Lock className="w-4 h-4" />
                    <span>Ingresar a SecureCode</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Nota técnica y estándar */}
          <div className="mt-6 pt-5 border-t border-slate-800/80 text-[11px] text-slate-500 space-y-2">
            <div className="flex items-center gap-2 text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>Valida vía <code className="bg-slate-950 px-1 py-0.5 rounded text-slate-300 font-mono">POST /api/v1/auth/token</code></span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <Cpu className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
              <span>Hash de contraseñas con Argon2id (RFC 9106)</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <Layers className="w-3.5 h-3.5 text-violet-400 shrink-0" />
              <span>Sesión respaldada por JSON Web Token (HS256)</span>
            </div>
          </div>
        </div>

        {/* Footer institucional */}
        <p className="text-center text-xs text-slate-600 mt-6 font-mono">
          SecureCode © 2026 · INACAP ES2 · Flujo L.E.R.
        </p>
      </div>
    </div>
  );
}
