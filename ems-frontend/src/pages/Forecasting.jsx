import { useQuery } from "@tanstack/react-query";
import { Clock3, LineChart, Plug, Sun } from "lucide-react";
import { PageHeader, Loading, Badge, Empty } from "../components/ui";
import KpiCard from "../components/KpiCard";
import { ForecastChart } from "../components/EnergyChart";
import { useHouseId } from "../hooks/useHouseId";
import { forecastingApi } from "../api/endpoints";
import { fmt, fmtDate, fmtTime } from "../utils/format";

function toSeries(points) {
  return (points || []).map((p) => ({ label: fmtTime(p.horizon), prevu: p.value }));
}

function toRows(production, consumption) {
  const rows = new Map();
  (production || []).forEach((p) => {
    rows.set(p.horizon, { horizon: p.horizon, production: p.value });
  });
  (consumption || []).forEach((p) => {
    rows.set(p.horizon, { ...(rows.get(p.horizon) || { horizon: p.horizon }), consumption: p.value });
  });
  return Array.from(rows.values())
    .sort((a, b) => new Date(a.horizon) - new Date(b.horizon))
    .slice(0, 12);
}

export default function Forecasting() {
  const houseId = useHouseId();

  const { data: models, isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: forecastingApi.models,
  });
  const { data: prodPred } = useQuery({
    queryKey: ["predict", "production", houseId],
    queryFn: () => forecastingApi.predict({ target: "production",  hours: 24, house: houseId }),
    enabled: !!houseId,
    retry: false,
  });
  const { data: consPred } = useQuery({
    queryKey: ["predict", "consumption", houseId],
    queryFn: () => forecastingApi.predict({ target: "consumption", hours: 24, house: houseId }),
    enabled: !!houseId,
    retry: false,
  });

  if (isLoading) return <Loading />;

  const modelList  = models?.results || models || [];
  const prodModel  = modelList.find((m) => m.target === "production"  && m.is_active);
  const consModel  = modelList.find((m) => m.target === "consumption" && m.is_active);
  const production  = prodPred?.predictions || [];
  const consumption = consPred?.predictions || [];
  const previewRows = toRows(production, consumption);

  return (
    <>
      <PageHeader
        title="Prévisions horaires"
        subtitle="Production et consommation estimées pour les prochaines heures du micro-réseau sélectionné."
      />

      {/* KPI grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard icon={Sun}       tone="green" label="Production dans 1h"    value={fmt(production[0]?.value)}  unit="kW" hint={prodModel?.algorithm  || "Profil horaire"} />
        <KpiCard icon={Plug}      tone="blue"  label="Consommation dans 1h"  value={fmt(consumption[0]?.value)} unit="kW" hint={consModel?.algorithm  || "Profil horaire"} />
        <KpiCard icon={Clock3}    tone="amber" label="Horizon affiché"        value="24" unit="h" hint="de 1h à 24h" />
        <KpiCard icon={LineChart} tone="navy"  label="Stratégies actives"     value={modelList.filter((m) => m.is_active).length} hint="production + consommation" />
      </div>

      {/* Graphiques */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <h3 className="mb-4 font-semibold text-navy dark:text-white">
            Prévision de production photovoltaïque
          </h3>
          {production.length ? (
            <ForecastChart data={toSeries(production)} />
          ) : (
            <Empty message="Aucune prévision de production disponible." />
          )}
        </div>
        <div className="card p-5">
          <h3 className="mb-4 font-semibold text-navy dark:text-white">
            Prévision de consommation énergétique
          </h3>
          {consumption.length ? (
            <ForecastChart data={toSeries(consumption)} />
          ) : (
            <Empty message="Aucune prévision de consommation disponible." />
          )}
        </div>
      </div>

      {/* Tableau prochaines heures */}
      <div className="card mt-6 overflow-hidden">
        <h3 className="px-5 pt-5 pb-3 font-semibold text-navy dark:text-white">
          Prochaines heures
        </h3>
        {previewRows.length === 0 ? (
          <Empty message="Aucune prévision horaire disponible." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500 dark:bg-white/5">
              <tr>
                <th className="px-5 py-3 font-medium">Horizon</th>
                <th className="px-5 py-3 font-medium">Production prévue</th>
                <th className="px-5 py-3 font-medium">Consommation prévue</th>
              </tr>
            </thead>
            <tbody>
              {previewRows.map((row) => (
                <tr key={row.horizon} className="border-t border-slate-100 dark:border-white/5">
                  <td className="px-5 py-2.5 font-medium text-slate-600 dark:text-slate-300">{fmtDate(row.horizon)}</td>
                  <td className="px-5 py-2.5 font-semibold text-energy">
                    {row.production != null ? `${fmt(row.production)} kW` : "—"}
                  </td>
                  <td className="px-5 py-2.5 font-semibold text-electric">
                    {row.consumption != null ? `${fmt(row.consumption)} kW` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Stratégies */}
      <div className="card mt-6 overflow-hidden">
        <h3 className="px-5 pt-5 pb-3 font-semibold text-navy dark:text-white">
          Stratégies de prévision
        </h3>
        {modelList.length === 0 ? (
          <Empty message="Aucune stratégie disponible pour le moment." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500 dark:bg-white/5">
              <tr>
                <th className="px-5 py-3 font-medium">Cible</th>
                <th className="px-5 py-3 font-medium">Algorithme</th>
                <th className="px-5 py-3 font-medium">Rôle</th>
                <th className="px-5 py-3 font-medium">Statut</th>
              </tr>
            </thead>
            <tbody>
              {modelList.map((m) => (
                <tr key={m.id} className="border-t border-slate-100 dark:border-white/5">
                  <td className="px-5 py-2.5 font-medium text-navy dark:text-white">{m.target}</td>
                  <td className="px-5 py-2.5 text-slate-500">{m.algorithm}</td>
                  <td className="px-5 py-2.5 text-slate-500">Calcul horaire à partir des mesures récentes</td>
                  <td className="px-5 py-2.5">
                    <Badge value={m.is_active ? "VALID" : "INACTIVE"}>
                      {m.is_active ? "Actif" : "Archivé"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
