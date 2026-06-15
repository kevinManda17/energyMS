import { Link } from "react-router-dom";
import { Activity, LineChart, Zap, ShieldCheck } from "lucide-react";
import Logo from "./Logo";

const FEATURES = [
  { icon: Activity, title: "Supervision en temps réel", text: "Surveillez vos installations et performances 24h/24 et 7j/7." },
  { icon: LineChart, title: "Prévisions intelligentes", text: "Anticipez la production, la consommation et les besoins énergétiques." },
  { icon: Zap, title: "Décisions énergétiques", text: "Système expert flou pour optimiser le micro-réseau automatiquement." },
  { icon: ShieldCheck, title: "Sécurité et fiabilité", text: "Vos données sont protégées par des technologies avancées." },
];

export default function AuthShell({ children }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Left brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-[#0B1220] via-navy to-[#0F3D57] p-12 text-white lg:flex">
        <Logo light />
        <div className="max-w-md">
          <h2 className="text-3xl font-bold leading-snug">
            La gestion intelligente de l'énergie pour des micro-réseaux durables
          </h2>
          <p className="mt-4 text-slate-300">
            EMS centralise, supervise et optimise tous vos actifs énergétiques
            pour une performance et une résilience maximales.
          </p>
          <div className="mt-8 space-y-5">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <div key={title} className="flex gap-3">
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/10">
                  <Icon size={18} />
                </div>
                <div>
                  <div className="font-semibold">{title}</div>
                  <div className="text-sm text-slate-300">{text}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-slate-400">
          © 2026 EMS — Energy Management System. Tous droits réservés.
        </p>
      </div>

      {/* Right form panel */}
      <div className="flex items-center justify-center bg-slate-50 p-6 dark:bg-[#071923]">
        <div className="w-full max-w-md">
          {children}
          <p className="mt-6 text-center text-xs text-slate-400">
            <Link to="/" className="hover:text-electric">← Retour à l'accueil</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
