import { useQuery } from "@tanstack/react-query";
import { BatteryCharging, Brain, ChevronRight, Plug, Scale, Sun, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader, Loading, Badge } from "../components/ui";
import KpiCard from "../components/KpiCard";
import { ProdConsoChart } from "../components/EnergyChart";
import { useHouseId } from "../hooks/useHouseId";
import { measurementsApi, decisionsApi, alertsApi } from "../api/endpoints";
import { fmt, fmtTime, fmtDate, ACTION_LABELS } from "../utils/format";

function byType(latest) {
  const map = {};
  (latest || []).forEach((m) => (map[m.measurement_type] = m));
  return map;
}

function buildSeries(history) {
  const rows = {};
  (history?.results || []).forEach((m) => {
    const label = fmtTime(m.timestamp);
    rows[label] = rows[label] || { label };
    if (m.measurement_type === "production")  rows[label].production  = m.value;
    if (m.measurement_type === "consumption") rows[label].consumption = m.value;
  });
  return Object.values(rows).reverse();
}

const SEV_BORDER = {
  CRITICAL: "border-l-danger",
  WARNING:  "border-l-solar",
  INFO:     "border-l-electric",
};

export default function Dashboard() {
  const houseId = useHouseId();

  const { data: latest, isLoading } = useQuery({
    queryKey: ["latest", houseId],
    queryFn: () => measurementsApi.latest(houseId),
    enabled: !!houseId,
  });
  const { data: history } = useQuery({
    queryKey: ["history-dash", houseId],
    queryFn: () => measurementsApi.history({ house: houseId, ordering: "-timestamp", page_size: 48 }),
    enabled: !!houseId,
  });
  const { data: decision } = useQuery({
    queryKey: ["decision-latest"],
    queryFn: decisionsApi.latest,
    retry: false,
  });
  const { data: alerts } = useQuery({
    queryKey: ["alerts", "recent"],
    queryFn: () => alertsApi.list({ page_size: 5 }),
  });

  if (isLoading) return <Loading />;

  const m          = byType(latest);
  const prod       = m.production?.value;
  const cons       = m.consumption?.value;
  const soc        = m.battery_soc?.value;
  const balance    = prod != null && cons != null ? prod - cons : null;
  const allAlerts  = (alerts?.results || []).slice(0, 2);
  const confidence = Math.min((decision?.confidence_score || 0) * 100, 100);

  return (
    <>
      <PageHeader
        title="Tableau de bord"
        subtitle="Vue d'ensemble de votre micro-réseau domestique en temps réel."
      />

      {/* KPI grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard icon={Sun}            tone="green" label="Production actuelle" value={fmt(prod)}       unit="kW" hint="Photovoltaïque" />
        <KpiCard icon={Plug}           tone="blue"  label="Consommation"         value={fmt(cons)}       unit="kW" hint="Charges actives" />
        <KpiCard icon={BatteryCharging}tone="amber" label="État batterie"         value={fmt(soc, 0)}    unit="%"  hint="State of charge" />
        <KpiCard
          icon={Scale}
          tone={balance != null && balance >= 0 ? "green" : "red"}
          label="Bilan énergétique"
          value={fmt(balance)}
          unit="kW"
          hint={balance != null ? (balance >= 0 ? "Surplus" : "Déficit") : "—"}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Chart */}
        <div className="card p-5 lg:col-span-2">
          <h3 className="mb-4 font-semibold text-navy dark:text-white">
            Production vs Consommation
          </h3>
          <ProdConsoChart data={buildSeries(history)} />
        </div>

        <div className="space-y-4">
          {/* Decision card */}
          <div className="card p-5">
            <h3 className="mb-4 flex items-center justify-between">
              <span className="flex items-center gap-2 text-sm font-semibold text-navy dark:text-white">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-500/15">
                  <Brain size={14} className="text-purple-600 dark:text-purple-400" />
                </span>
                Dernière décision
              </span>
              <Link
                to="/decisions"
                className="flex items-center gap-0.5 text-xs font-medium text-electric hover:underline"
              >
                Voir tout <ChevronRight size={12} />
              </Link>
            </h3>

            {decision ? (
              <>
                <p className="font-bold leading-snug text-electric line-clamp-2">
                  {decision.decision_label || ACTION_LABELS[decision.action] || decision.action}
                </p>
                <p className="mt-1 line-clamp-2 text-sm text-slate-500">{decision.reason}</p>

                {/* Confidence bar */}
                <div className="mt-3 space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Confiance</span>
                    <span className="font-semibold">{fmt(confidence, 0)}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${confidence}%`,
                        backgroundColor: confidence >= 70 ? "#16A34A" : confidence >= 40 ? "#F59E0B" : "#DC2626",
                      }}
                    />
                  </div>
                </div>

                <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
                  <Badge value={decision.alert_level || "INFO"}>{decision.alert_level || "INFO"}</Badge>
                  {fmtDate(decision.created_at)}
                </div>
              </>
            ) : (
              /* État vide : CTA pour lancer une évaluation */
              <div className="flex flex-col items-center gap-3 py-3 text-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-purple-100 dark:bg-purple-500/15">
                  <Brain size={22} className="text-purple-600 dark:text-purple-400" />
                </span>
                <p className="text-sm text-slate-400">Aucune décision enregistrée.</p>
                <Link
                  to="/decisions"
                  className="btn-primary gap-1.5 px-3 py-1.5 text-xs"
                >
                  <Zap size={13} strokeWidth={2.6} /> Lancer une évaluation
                </Link>
              </div>
            )}
          </div>

          {/* Recent alerts — max 2 visible + dropdown */}
          <div className="card p-5">
            <h3 className="mb-3 flex items-center justify-between">
              <span className="text-sm font-semibold text-navy dark:text-white">
                Alertes récentes
              </span>
              <Link
                to="/alerts"
                className="flex items-center gap-0.5 text-xs font-medium text-electric hover:underline"
              >
                Voir tout <ChevronRight size={12} />
              </Link>
            </h3>

            <ul className="space-y-2">
              {allAlerts.length === 0 && (
                <li className="text-sm text-slate-400">Aucune alerte active.</li>
              )}
              {allAlerts.map((a) => (
                <li
                  key={a.id}
                  className={`rounded-lg border border-l-4 border-transparent bg-slate-50 px-3 py-2 dark:bg-white/5 ${
                    SEV_BORDER[a.severity] || "border-l-slate-300 dark:border-l-slate-600"
                  }`}
                >
                  <div className="mb-1"><Badge value={a.severity} /></div>
                  <p className="line-clamp-2 text-xs leading-snug text-slate-600 dark:text-slate-300">
                    {a.message}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </>
  );
}
