import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { UserPlus } from "lucide-react";
import AuthShell from "../components/AuthShell";
import { authApi } from "../api/endpoints";
import { useAuthStore } from "../store/auth";

export default function Register() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    phone: "",
    first_name: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await authApi.register(form);
      await login(form.username, form.password);
      navigate("/dashboard");
    } catch (err) {
      const data = err.response?.data;
      setError(
        data ? Object.values(data).flat().join(" ") : "Inscription impossible."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell>
      <div className="card p-8">
        <h1 className="text-2xl font-bold text-navy dark:text-white">
          Créer un compte
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Remplissez les informations ci-dessous pour créer votre compte EMS.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium">Nom complet</label>
              <input className="input" value={form.first_name} onChange={set("first_name")} placeholder="Votre nom" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Identifiant</label>
              <input className="input" value={form.username} onChange={set("username")} placeholder="utilisateur" required />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Adresse e-mail</label>
            <input type="email" className="input" value={form.email} onChange={set("email")} placeholder="exemple@domaine.com" required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium">Téléphone</label>
              <input className="input" value={form.phone} onChange={set("phone")} placeholder="+243 81 234 5678" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Mot de passe</label>
              <input type="password" className="input" value={form.password} onChange={set("password")} placeholder="Min. 8 caractères" required />
            </div>
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <button className="btn-primary w-full" disabled={loading}>
            <UserPlus size={16} /> {loading ? "Création…" : "Créer mon compte"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-500">
          Vous avez déjà un compte ?{" "}
          <Link to="/login" className="font-semibold text-electric">
            Se connecter
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
