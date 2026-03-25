"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { useAppStore } from "@/lib/store";

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAppStore((s) => s.setAuth);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErro("");
    try {
      const data = await login(username, password);
      setAuth(data.token, data.username, data.plano);
      router.push("/workspace");
    } catch (err: any) {
      setErro(err.message ?? "Erro ao autenticar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="text-4xl font-bold tracking-tight">
            <span className="text-white">APEX</span>
            <span className="text-apex-400">-LEGAL</span>
          </div>
          <p className="text-gray-400 mt-2 text-sm">PERFORMANCE · Workspace Jurídico com IA</p>
        </div>

        {/* Card */}
        <div className="card p-8">
          <h1 className="text-xl font-semibold text-white mb-6">Entrar</h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Usuário</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="seu.usuario"
                required
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3
                           text-white placeholder-gray-500 text-sm
                           focus:outline-none focus:border-apex-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Senha</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3
                           text-white placeholder-gray-500 text-sm
                           focus:outline-none focus:border-apex-500 transition-colors"
              />
            </div>

            {erro && (
              <p className="text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {erro}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-apex-600 hover:bg-apex-500 disabled:opacity-50
                         text-white font-medium py-3 rounded-lg text-sm transition-colors"
            >
              {loading ? "Autenticando…" : "Entrar"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-gray-600 mt-6">
          APEX-LEGAL PERFORMANCE v2.0 · Powered by Claude
        </p>
      </div>
    </div>
  );
}
