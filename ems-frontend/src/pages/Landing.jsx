import { Link } from "react-router-dom";
import { Activity, LineChart, Workflow, Bell, Cpu, ShieldCheck, ArrowRight } from "lucide-react";
import PublicHeader from "../components/PublicHeader";

const FEATURES = [
  { icon: Activity, title: "Supervision temps réel", text: "Production, consommation, batterie et état des équipements en direct via IoT/MQTT." },
  { icon: LineChart, title: "Prévisions par ML", text: "Random Forest pour anticiper la production photovoltaïque et la consommation." },
  { icon: Workflow, title: "Système expert flou", text: "Décisions automatiques : charger, délester, alimenter, notifier." },
  { icon: Bell, title: "Alertes intelligentes", text: "Notifications critiques sur le web et le mobile en cas d'anomalie." },
  { icon: Cpu, title: "Edge computing", text: "Passerelle locale Raspberry Pi avec cache et synchronisation cloud." },
  { icon: ShieldCheck, title: "Sécurisé & extensible", text: "Authentification JWT, architecture dockerisée, prête pour AWS." },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50/60 to-white">
      <PublicHeader />

      <section className="mx-auto max-w-7xl px-6 py-20 text-center">
        <span className="badge bg-blue-50 text-electric">⚡ Micro-réseau domestique intelligent</span>
        <h1 className="mx-auto mt-6 max-w-3xl text-5xl font-extrabold leading-tight text-navy">
          Supervisez, prévoyez et optimisez votre énergie solaire
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-600">
          EMS combine IoT, Machine Learning et système expert flou pour gérer
          intelligemment la production, le stockage et la consommation de votre
          micro-réseau domestique.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link to="/register" className="btn-primary">
            Commencer gratuitement <ArrowRight size={16} />
          </Link>
          <Link to="/pricing" className="btn-ghost">Voir les offres</Link>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-7xl px-6 py-16">
        <h2 className="text-center text-3xl font-bold text-navy">
          Une plateforme énergétique complète
        </h2>
        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="card p-6">
              <div className="grid h-12 w-12 place-items-center rounded-xl bg-blue-50 text-electric">
                <Icon size={22} />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-navy">{title}</h3>
              <p className="mt-2 text-sm text-slate-600">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="contact" className="mx-auto my-16 max-w-5xl rounded-3xl bg-gradient-to-br from-navy to-[#0F3D57] px-6 py-14 text-center text-white">
        <h2 className="text-3xl font-bold">Prêt à optimiser votre énergie ?</h2>
        <p className="mx-auto mt-3 max-w-xl text-slate-300">
          Créez votre compte et connectez votre premier micro-réseau en quelques minutes.
        </p>
        <Link to="/register" className="btn mt-6 bg-white text-navy hover:bg-slate-100">
          Créer un compte
        </Link>
      </section>

      <footer className="border-t border-slate-100 py-8 text-center text-sm text-slate-400">
        © 2026 EMS — Energy Management System.
      </footer>
    </div>
  );
}
