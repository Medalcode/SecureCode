import React, { useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { loginUser } from '../api/client';

export default function LoginView({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setHasError(false);
    setErrorMessage('');

    if (!username.trim() || !password) {
      setHasError(true);
      setErrorMessage('Usuario o contraseña incorrectos. Verifique sus datos.');
      return;
    }

    setIsLoading(true);
    const result = await loginUser(username, password);
    setIsLoading(false);

    if (!result.success) {
      setHasError(true);
      // Mensaje de la especificación oficial del Estado de Error
      setErrorMessage('Usuario o contraseña incorrectos. Verifique sus datos.');
    } else {
      if (onLoginSuccess) {
        onLoginSuccess(result.data);
      }
    }
  };

  return (
    <div 
      className="min-h-screen w-full flex items-center justify-center p-4"
      style={{ backgroundColor: '#F4F6FA' }}
    >
      {/* Contenedor: Posición Centro, Fondo #FFFFFF, Borde Radio 8px, Sombra Suave */}
      <div 
        className="w-full max-w-[400px] border border-slate-200 shadow-md p-8 sm:p-10"
        style={{ 
          backgroundColor: '#FFFFFF',
          borderRadius: '8px'
        }}
      >
        {/* Encabezado */}
        <div className="text-center mb-8">
          <h1 
            className="text-2xl sm:text-3xl font-extrabold tracking-wide"
            style={{ color: '#213F8B' }}
          >
            SECURECODE
          </h1>
          <p 
            className="text-sm mt-1 font-normal"
            style={{ color: '#555555' }}
          >
            Evaluación automatizada de controles
          </p>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Campo: Usuario */}
          <div>
            <label 
              htmlFor="username" 
              className="block text-sm font-medium mb-1.5"
              style={{ color: '#555555' }}
            >
              Usuario
            </label>
            <input
              id="username"
              type="email"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (hasError) setHasError(false);
              }}
              placeholder="auditor@empresa.com"
              disabled={isLoading}
              autoComplete="email"
              required
              className="w-full px-3.5 py-2.5 bg-white text-sm text-slate-800 placeholder-slate-400 focus:outline-none transition disabled:bg-slate-50"
              style={{
                borderRadius: '8px',
                border: hasError ? '1px solid #D9534F' : '1px solid #D1D5DB',
              }}
            />
          </div>

          {/* Campo: Contraseña */}
          <div>
            <label 
              htmlFor="password" 
              className="block text-sm font-medium mb-1.5"
              style={{ color: '#555555' }}
            >
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (hasError) setHasError(false);
              }}
              placeholder="••••••••••••"
              disabled={isLoading}
              autoComplete="current-password"
              required
              className="w-full px-3.5 py-2.5 bg-white text-sm text-slate-800 placeholder-slate-400 focus:outline-none transition disabled:bg-slate-50"
              style={{
                borderRadius: '8px',
                border: hasError ? '1px solid #D9534F' : '1px solid #D1D5DB',
              }}
            />
          </div>

          {/* Botón: Ingresar */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 font-semibold text-sm transition shadow-sm hover:opacity-95 active:opacity-90 disabled:opacity-60 cursor-pointer"
              style={{
                backgroundColor: '#213F8B',
                color: '#FFFFFF',
                borderRadius: '8px',
              }}
            >
              {isLoading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </div>
        </form>

        {/* Alerta: Error de autenticación */}
        {hasError && (
          <div 
            className="mt-5 p-3 flex items-center gap-2.5 text-xs animate-in fade-in duration-150"
            style={{
              backgroundColor: '#FDF2F2',
              border: '1px solid #F5C6CB',
              borderRadius: '8px',
              color: '#C0392B',
            }}
          >
            <AlertCircle className="w-4 h-4 shrink-0" style={{ color: '#C0392B' }} />
            <span className="font-medium">
              {errorMessage || 'Usuario o contraseña incorrectos. Verifique sus datos.'}
            </span>
          </div>
        )}

      </div>
    </div>
  );
}
