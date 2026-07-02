import { useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Clock3, LineChart, Plug, Sun } from "lucide-react";
import { PageHeader, Loading, Badge, Empty } from "../components/ui";
import KpiCard from "../components/KpiCard";
import { ForecastChart } from "../components/EnergyChart";
import { useHouseId } from "../hooks/useHouseId";
import { forecastingApi } from "../api/endpoints";
import { fmt, fmtDate, fmtTime } from "../utils/format";

const STEP_MINUTES = 10;
const PAGE_SIZE = 24; // 24 x 10 min = 4h per page

const MODEL_ROLE = {
  keras_gru:
    "Prévision glissante (rollout autorégressif) : chaque pas de 10 min réutilise la prédiction précédente pour avancer dans le temps, à partir de l'historique récent de la maison.",
  keras_lstm:
    "Réseau de neurones séquentiel (fenêtre d'historique récent).",
  keras_cnn_lstm:
    "Réseau de neurones séquentiel (fenêtre d'historique récent).",
  keras_lstm_att:
    "Réseau de neurones séquentiel avec attention (fenêtre d'historique récent).",
  sklearn:
    "Prédiction directe à chaque pas de 10 min à partir de la météo prévue pour cet horizon et des dernières mesures des panneaux — pas d'historique figé, donc pas de valeurs répétées.",
  profile:
    "Formule de repli (aucun modèle IA actif pour cette cible) : profil horaire type combiné aux mesures récentes.",
};

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
  return Array.from(rows.values()).sort((a, b) => new Date(a.horizon) - new Date(b.horizon));
}

export default function Forecasting() {
  const houseId = useHouseId();
  const [page, setPage] = useState(1);

  const { data: models, isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: forecastingApi.models,
  });
  const { data: prodPred } = useQuery({
    queryKey: ["predict", "production", houseId, page],
    queryFn: () =>
      forecastingApi.predict({
        target: "production", hours: 24, house: houseId,
        step_minutes: STEP_MINUTES, page, page_size: PAGE_SIZE,
      }),
    enabled: !!houseId,
    retry: false,
    placeholderData: keepPreviousData,
  });
  const { data: consPred } = useQuery({
    queryKey: ["predict", "consumption", houseId, page],
    queryFn: () =>
      forecastingApi.predict({
        target: "consumption", hours: 24, house: houseId,
        step_minutes: STEP_MINUTES, page, page_size: PAGE_SIZE,
      }),
    enabled: !!houseId,
    retry: false,
    placeholderData: keepPreviousData,
  });

  if (isLoading) return <Loading />;

  const modelList  = models?.results || models || [];
  const prodModel  = modelList.find((m) => m.target === "production"  && m.is_active);
  const consModel  = modelList.find((m) => m.target === "consumption" && m.is_active);
  const production  = prodPred?.predictions || [];
  const consumption = consPred?.predictions || [];
  const rows = toRows(production, consumption);
  const pagination = prodPred?.pagination || consPred?.pagination;

  return (
    <>
      <PageHeader
        title="Prévisions"
        subtitle={`Production et consommation estimées par pas de ${STEP_MINUTES} minutes pour le micro-réseau sélectionné.`}
      />

      {/* KPI grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard icon={Sun}       tone="green" label={`Production dans ${STEP_MINUTES} min`}    value={fmt(production[0]?.value)}  unit="kW" hint={prodModel?.algorithm  || "Profil horaire"} />
        <KpiCard icon={Plug}      tone="blue"  label={`Consommation dans ${STEP_MINUTES} min`}  value={fmt(consumption[0]?.value)} unit="kW" hint={consModel?.algorithm  || "Profil horaire"} />
        <KpiCard icon={Clock3}    tone="amber" label="Horizon affiché"        value="24" unit="h" hint={`pas de ${STEP_MINUTES} min, page ${pagination?.page || 1}/${pagination?.num_pages || 1}`} />
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

      {/* Tableau des prochains pas de temps */}
      <div className="card mt-6 overflow-hidden">
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <h3 className="font-semibold text-navy dark:text-white">
            Prochains pas de {STEP_MINUTES} minutes
          </h3>
          {pagination && (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <button
                type="button"
                className="btn-secondary !px-2 !py-1.5 disabled:opacity-40"
                disabled={!pagination.has_previous}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                aria-label="Page précédente"
              >
                <ChevronLeft size={16} />
              </button>
              <span>Page {pagination.page} / {pagination.num_pages}</span>
              <button
                type="button"
                className="btn-secondary !px-2 !py-1.5 disabled:opacity-40"
                disabled={!pagination.has_next}
                onClick={() => setPage((p) => p + 1)}
                aria-label="Page suivante"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          )}
        </div>
        {rows.length === 0 ? (
          <Empty message="Aucune prévision disponible." />
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
              {rows.map((row) => (
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
          Modèles utilisés pour ces prévisions
        </h3>
        {modelList.length === 0 ? (
          <Empty message="Aucune stratégie disponible pour le moment." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500 dark:bg-white/5">
              <tr>
                <th className="px-5 py-3 font-medium">Cible</th>
                <th className="px-5 py-3 font-medium">Algorithme</th>
                <th className="px-5 py-3 font-medium">Fonctionnement</th>
                <th className="px-5 py-3 font-medium">Précision (R² / RMSE)</th>
                <th className="px-5 py-3 font-medium">Statut</th>
              </tr>
            </thead>
            <tbody>
              {modelList.map((m) => (
                <tr key={m.id} className="border-t border-slate-100 dark:border-white/5">
                  <td className="px-5 py-2.5 font-medium text-navy dark:text-white">{m.target}</td>
                  <td className="px-5 py-2.5 text-slate-500">{m.algorithm}</td>
                  <td className="px-5 py-2.5 text-slate-500 max-w-sm">{MODEL_ROLE[m.model_type] || "—"}</td>
                  <td className="px-5 py-2.5 text-slate-500">
                    {m.metrics?.R2 != null ? Number(m.metrics.R2).toFixed(3) : "—"}
                    {" / "}
                    {m.metrics?.RMSE != null ? Number(m.metrics.RMSE).toFixed(3) : "—"}
                  </td>
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
