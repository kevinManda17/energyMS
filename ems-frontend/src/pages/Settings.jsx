import { useState } from "react";
import { User, Palette, Bot, ShieldCheck } from "lucide-react";
import { PageHeader } from "../components/ui";
import { useAuthStore } from "../store/auth";
import { useUIStore } from "../store/ui";

const TABS = [
  ["profile", "Profil", User],
  ["display", "Affichage", Palette],
  ["security", "Sécurité", ShieldCheck],
  ["agent", "Agent IA", Bot],
];

export default function SettingsPage() {
  const { user } = useAuthStore();
  const { theme, toggleTheme } = useUIStore();
  const [tab, setTab] = useState("profile");

  return (
    <>
      <PageHeader title="Paramètres" subtitle="Configuration du système et préférences." />

      <div className="mb-6 flex flex-wrap gap-2">
        {TABS.map(([id, label, Icon]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={tab === id ? "btn-primary" : "btn-ghost"}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {tab === "profile" && (
        <div className="card max-w-xl space-y-4 p-6">
          <h3 className="font-semibold text-navy dark:text-white">Profil utilisateur</h3>
          <Field label="Identifiant" value={user?.username} />
          <Field label="E-mail" value={user?.email} />
          <Field label="Téléphone" value={user?.phone || "—"} />
          <Field label="Rôle" value={user?.role} />
        </div>
      )}

      {tab === "display" && (
        <div className="card max-w-xl space-y-4 p-6">
          <h3 className="font-semibold text-navy dark:text-white">Préférences d'affichage</h3>
          <div className="flex items-center justify-between">
            <span>Thème {theme === "dark" ? "sombre" : "clair"}</span>
            <button className="btn-ghost" onClick={toggleTheme}>
              Basculer
            </button>
          </div>
          <Field label="Langue" value="Français" />
          <Field label="Unité de mesure" value="Métrique (kWh, °C, V, A)" />
        </div>
      )}

      {tab === "security" && (
        <div className="card max-w-xl space-y-4 p-6">
          <h3 className="font-semibold text-navy dark:text-white">Sécurité</h3>
          <p className="text-sm text-slate-500">
            Authentification par JWT. La rotation des tokens et le rafraîchissement
            sont gérés automatiquement.
          </p>
          <Field label="Authentification" value="JWT (SimpleJWT)" />
        </div>
      )}

      {tab === "agent" && (
        <div className="card max-w-xl space-y-3 p-6">
          <h3 className="flex items-center gap-2 font-semibold text-navy dark:text-white">
            <Bot size={18} /> Agent conversationnel
          </h3>
          <span className="badge bg-slate-100 text-slate-500">Désactivé — perspective future</span>
          <p className="text-sm text-slate-500">
            L'agent conversationnel n'est pas développé dans cette version. Il est
            prévu comme module futur (voir docs/future-agent.md).
          </p>
        </div>
      )}
    </>
  );
}

function Field({ label, value }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  );
}
