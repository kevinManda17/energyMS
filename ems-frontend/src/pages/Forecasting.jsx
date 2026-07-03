import { useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Plug, Sun } from "lucide-react";
import { PageHeader, Loading, Empty } from "../components/ui";
import KpiCard from "../components/KpiCard";
import { ForecastChart } from "../components/EnergyChart";
import { useHouseId } from "../hooks/useHouseId";
import { forecastingApi } from "../api/endpoints";
import { fmt, fmtDate, fmtTime } from "../utils/format";

const STEP_MINUTES = 10;
const PAGE_SIZE = 24; // 24 x 10 min = 4h par page
const ONE_HOUR_INDEX = 60 / STEP_MINUTES - 1; // point situé à +1 h

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

function usePredict(target, houseId, page) {
  return useQuery({
    queryKey: ["predict", target, houseId, page],
    queryFn: () =>
      forecastingApi.predict({
        target, hours: 24, house: houseId,
        step_minutes: STEP_MINUTES, page, page_size: PAGE_SIZE,
      }),
    enabled: !!houseId,
    retry: false,
    placeholderData: keepPreviousData,
  });
}

export default function Forecasting() {
  const houseId = useHouseId();
  const [page, setPage] = useState(1);

  // Page 1 (clé stable) : alimente les cartes "dans 10 min / dans 1 h",
  // qui ne doivent pas bouger quand on feuillette le tableau.
  const { data: prodFirst, isLoading: loadingProd } = usePredict("production", houseId, 1);
  const { data: consFirst, isLoading: loadingCons } = usePredict("consumption", houseId, 1);
  // Page courante : alimente les graphiques et le tableau.
  const { data: prodPred } = usePredict("production", houseId, page);
  const { data: consPred } = usePredict("consumption", houseId, page);

  if (houseId && (loadingProd || loadingCons)) return <Loading />;

  const production  = prodPred?.predictions || [];
  const consumption = consPred?.predictions || [];
  const rows = toRows(production, consumption);
  const pagination = prodPred?.pagination || consPred?.pagination;

  const prod10 = prodFirst?.predictions?.[0];
  const cons10 = consFirst?.predictions?.[0];
  const prod60 = prodFirst?.predictions?.[ONE_HOUR_INDEX];
  const cons60 = consFirst?.predictions?.[ONE_HOUR_INDEX];

  return (
    <>
      <PageHeader
        title="Prévisions"
        subtitle="Production et consommation estimées par pas de 10 minutes, en tenant compte de l'heure de la journée."
      />

      {/* KPI grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard icon={Sun}  tone="green" label="Production dans 10 min"   value={fmt(prod10?.value)} unit="kW" hint={prod10 ? `à ${fmtTime(prod10.horizon)}` : "—"} />
        <KpiCard icon={Plug} tone="blue"  label="Consommation dans 10 min" value={fmt(cons10?.value)} unit="kW" hint={cons10 ? `à ${fmtTime(cons10.horizon)}` : "—"} />
        <KpiCard icon={Sun}  tone="amber" label="Production dans 1 h"      value={fmt(prod60?.value)} unit="kW" hint={prod60 ? `à ${fmtTime(prod60.horizon)}` : "—"} />
        <KpiCard icon={Plug} tone="navy"  label="Consommation dans 1 h"    value={fmt(cons60?.value)} unit="kW" hint={cons60 ? `à ${fmtTime(cons60.horizon)}` : "—"} />
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
            Prochaines prévisions <span className="text-sm font-normal text-slate-400">(horizon 24 h)</span>
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
    </>
  );
}
