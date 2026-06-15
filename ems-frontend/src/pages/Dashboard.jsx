import { useQuery } from "@tanstack/react-query";
import { Sun, Plug, BatteryCharging, Scale, Workflow } from "lucide-react";
import { PageHeader, Loading, Badge } from "../components/ui";
import KpiCard from "../components/KpiCard";
import { ProdConsoChart } from "../components/EnergyChart";
import { useHouseId } from "../hooks/useHouseId";
import {
  measurementsApi,
  decisionsApi,
  alertsApi,
} from "../api/endpoints";
import { fmt, fmtTime, fmtDate, ACTION_LABELS } from "../utils/format";

function byType(latest) {
  const map = {};
  (latest || []).forEach((m) => (map[m.measurement_type] = m));
  return map;
}

function buildSeries(history) {
  // Group last points by hour label, merging production & consumption.
  const rows = {};
  (history?.results || []).forEach((m) => {
    const label = fmtTime(m.timestamp);
    rows[label] = rows[label] || { label };
    if (m.measurement_type === "production") rows[label].production = m.value;
    if (m.measurement_type === "consumption") rows[label].consumption = m.value;
  });
  return Object.values(rows).reverse();
}

export default function Dashboard() {
  const houseId = useHouseId();

  const { data: latest, isLoading } = useQuery({
    queryKey: ["latest", houseId],
    queryFn: () => measurementsApi.latest(houseId),
    enabled: !!houseId,
  });
  const { data: history } = useQuery({
    queryKey: ["history-dash", houseId],
    queryFn: () =>
      measurementsApi.history({ house: houseId, ordering: "-timestamp", page_size: 48 }),
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

  const m = byType(latest);
  const prod = m.production?.value;
  const cons = m.consumption?.value;
  const soc = m.battery_soc?.value;
  const balance = prod != null && cons != null ? prod - cons : null;
  const recentAlerts = alerts?.results || [];

  return (
    <>
      <PageHeader
        title="Tableau de bord"
        subtitle="Vue d'ensemble de votre micro-réseau domestique en temps réel."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard icon={Sun} tone="green" label="Production actuelle" value={fmt(prod)} unit="kW" hint="Photovoltaïque" />
        <KpiCard icon={Plug} tone="blue" label="Consommation" value={fmt(cons)} unit="kW" hint="Charges actives" />
        <KpiCard icon={BatteryCharging} tone="amber" label="État batterie" value={fmt(soc, 0)} unit="%" hint="State of charge" />
        <KpiCard
          icon={Scale}
          tone={balance >= 0 ? "green" : "red"}
          label="Bilan énergétique"
          value={fmt(balance)}
          unit="kW"
          hint={balance >= 0 ? "Surplus" : "Déficit"}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <h3 className="mb-4 font-semibold text-navy dark:text-white">
            Production vs Consommation
          </h3>
          <ProdConsoChart data={buildSeries(history)} />
        </div>

        <div className="space-y-6">
          <div className="card p-5">
            <h3 className="mb-3 flex items-center gap-2 font-semibold text-navy dark:text-white">
              <Workflow size={18} /> Dernière décision
            </h3>
            {decision ? (
              <>
                <div className="text-lg font-bold text-electric">
                  {ACTION_LABELS[decision.action] || decision.action}
                </div>
                <p className="mt-1 text-sm text-slate-500">{decision.reason}</p>
                <div className="mt-3 text-xs text-slate-400">
                  Confiance : {fmt(decision.confidence_score * 100, 0)}% · {fmtDate(decision.created_at)}
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-400">Aucune décision pour l'instant.</p>
            )}
          </div>

          <div className="card p-5">
            <h3 className="mb-3 font-semibold text-navy dark:text-white">Alertes récentes</h3>
            <ul className="space-y-3">
              {recentAlerts.length === 0 && (
                <li className="text-sm text-slate-400">Aucune alerte.</li>
              )}
              {recentAlerts.map((a) => (
                <li key={a.id} className="flex items-start gap-2 text-sm">
                  <Badge value={a.severity} />
                  <span className="text-slate-600 dark:text-slate-300">{a.message}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </>
  );
}
