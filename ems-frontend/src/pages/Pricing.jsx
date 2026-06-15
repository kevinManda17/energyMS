import { Link } from "react-router-dom";
import { Check } from "lucide-react";
import PublicHeader from "../components/PublicHeader";

const PLANS = [
  {
    name: "Starter",
    price: "19",
    tag: "Pour les particuliers et petits foyers.",
    features: [
      "Supervision en temps réel",
      "Suivi production / consommation",
      "Alertes intelligentes",
      "Historique des données (12 mois)",
      "Rapports mensuels",
      "Support par e-mail",
    ],
  },
  {
    name: "Pro",
    price: "49",
    tag: "Pour maisons avancées, PME et petits sites.",
    popular: true,
    features: [
      "Tout dans Starter",
      "Prévisions énergétiques (IA)",
      "Gestion de batterie & stockage",
      "Historique des données (24 mois)",
      "Rapports PDF avancés",
      "Support prioritaire",
    ],
  },
  {
    name: "Enterprise",
    price: "99",
    tag: "Pour organisations, multi-sites et micro-réseaux.",
    features: [
      "Tout dans Pro",
      "Support multi-sites illimité",
      "Gestion multi-utilisateurs & rôles",
      "API & intégrations avancées",
      "Rapports personnalisés",
      "Support dédié 24/7",
    ],
  },
];

export default function Pricing() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50/60 to-white">
      <PublicHeader />
      <section className="mx-auto max-w-7xl px-6 py-16 text-center">
        <h1 className="text-4xl font-extrabold text-navy">
          Choisissez l'offre adaptée à votre gestion énergétique
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-slate-600">
          Nos plans vous aident à surveiller, prédire et optimiser votre
          consommation d'énergie pour vos maisons, sites et micro-réseaux.
        </p>

        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {PLANS.map((p) => (
            <div
              key={p.name}
              className={`card relative p-8 text-left ${
                p.popular ? "ring-2 ring-electric" : ""
              }`}
            >
              {p.popular && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-electric px-3 py-1 text-xs font-semibold text-white">
                  Le plus populaire
                </span>
              )}
              <h3 className="text-lg font-bold text-navy">{p.name}</h3>
              <p className="mt-1 text-sm text-slate-500">{p.tag}</p>
              <div className="mt-4">
                <span className="text-4xl font-extrabold text-navy">{p.price} $</span>
                <span className="text-sm text-slate-400"> /mois</span>
              </div>
              <ul className="mt-6 space-y-3 text-sm">
                {p.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-slate-600">
                    <Check size={16} className="text-energy" /> {f}
                  </li>
                ))}
              </ul>
              <Link
                to="/register"
                className={`mt-8 w-full ${p.popular ? "btn-primary" : "btn-ghost"}`}
              >
                Choisir cette offre
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
