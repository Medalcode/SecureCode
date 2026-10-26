import React, { useState } from 'react';
import { loginUser } from '../api/client';

export default function LoginView({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    if (!username.trim() || !password) {
      setErrorMessage('Por favor ingrese usuario y contraseña.');
      return;
    }

    setIsLoading(true);
    const result = await loginUser(username, password);
    setIsLoading(false);

    if (!result.success) {
      // Conforme a la Tabla 19 del informe oficial:
      // "Credenciales inválidas -> Aviso rojo bajo el formulario. Revisar datos y reintentar."
      setErrorMessage(
        result.status === 401
          ? 'Credenciales inválidas. Revisar datos y reintentar.'
          : (result.message || 'Error de conexión con el servicio. Reintentar más tarde.')
      );
    } else {
      if (onLoginSuccess) {
        onLoginSuccess(result.data);
      }
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-[#f1f5f9]">
      {/* Contenedor: Posición Centro, Borde Sutil, Fondo Blanco, Sombra Suave */}
      <div className="w-full max-w-[420px] bg-white border border-slate-200/90 rounded-2xl p-8 sm:p-10 shadow-lg shadow-slate-200/60">
        
        {/* Encabezado */}
        <div className="text-center mb-8">
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-wider text-[#0f2744]">
            SECURECODE
          </h1>
          <p className="text-sm text-slate-500 mt-2 font-normal">
            Evaluación automatizada de controles
          </p>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Campo: Usuario */}
          <div>
            <label 
              htmlFor="username" 
              className="block text-sm font-medium text-slate-600 mb-1.5"
            >
              Usuario
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isLoading}
              autoComplete="username"
              required
              className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0f2744]/20 focus:border-[#0f2744] transition disabled:bg-slate-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Campo: Contraseña */}
          <div>
            <label 
              htmlFor="password" 
              className="block text-sm font-medium text-slate-600 mb-1.5"
            >
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              autoComplete="current-password"
              required
              className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0f2744]/20 focus:border-[#0f2744] transition disabled:bg-slate-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Botón: Ingresar (Primario - Azul Marino) */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 bg-[#0f2744] hover:bg-[#16375f] active:bg-[#0b1c31] text-white font-medium rounded-lg text-sm transition shadow-sm disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center gap-2"
            >
              {isLoading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </div>

          {/* Aviso rojo bajo el formulario (según Tabla 19 del informe) */}
          {errorMessage && (
            <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs text-center font-medium">
              {errorMessage}
            </div>
          )}
        </form>

      </div>
    </div>
  );
}
