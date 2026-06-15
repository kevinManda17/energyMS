import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogIn, Mail, Lock } from "lucide-react";
import AuthShell from "../components/AuthShell";
import { useAuthStore } from "../store/auth";

export default function Login() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo12345");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch {
      setError("Identifiants invalides. Vérifiez vos informations.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell>
      <div className="card p-8">
        <h1 className="text-center text-2xl font-bold text-navy dark:text-white">
          Connexion
        </h1>
        <p className="mt-1 text-center text-sm text-slate-500">
          Accédez à votre plateforme EMS
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Identifiant</label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 text-slate-400" size={16} />
              <input
                className="input pl-9"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="demo"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Mot de passe</label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 text-slate-400" size={16} />
              <input
                type="password"
                className="input pl-9"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <button className="btn-primary w-full" disabled={loading}>
            <LogIn size={16} /> {loading ? "Connexion…" : "Se connecter"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-500">
          Vous n'avez pas de compte ?{" "}
          <Link to="/register" className="font-semibold text-electric">
            S'inscrire
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
