import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Brain, Target, RefreshCw } from "lucide-react";
import { PageHeader, Loading, Badge } from "../components/ui";
import KpiCard from "../components/KpiCard";
import { ForecastChart } from "../components/EnergyChart";
import { forecastingApi } from "../api/endpoints";
import { fmt, fmtTime } from "../utils/format";

function toSeries(points) {
  return (points || []).map((p) => ({
    label: fmtTime(p.horizon),
    prevu: p.value,
  }));
}

export default function Forecasting() {
  const qc = useQueryClient();

  const { data: models, isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: forecastingApi.models,
  });
  const { data: prodPred } = useQuery({
    queryKey: ["predict", "production"],
    queryFn: () => forecastingApi.predict({ target: "production", hours: 24 }),
    retry: false,
  });
  const { data: consPred } = useQuery({
    queryKey: ["predict", "consumption"],
    queryFn: () => forecastingApi.predict({ target: "consumption", hours: 24 }),
    retry: false,
  });

  const train = useMutation({
    mutationFn: (target) => forecastingApi.train(target),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["models"] });
      qc.invalidateQueries({ queryKey: ["predict"] });
    },
  });

  if (isLoading) return <Loading />;

  const modelList = models?.results || models || [];
  const prodModel = modelList.find((m) => m.target === "production" && m.is_active);
  const avgR2 = modelList.length
    ? modelList.reduce((s, m) => s + (m.r2 || 0), 0) / modelList.length
    : 0;

  return (
    <>
      <PageHeader
        title="Prévisions"
        subtitle="Anticipez la production et la consommation énergétique du micro-réseau."
        actions={
          <>
            <button className="btn-ghost" onClick={() => train.mutate("production")} disabled={train.isPending}>
              <RefreshCw size={16} /> Entraîner PV
            </button>
            <button className="btn-primary" onClick={() => train.mutate("consumption")} disabled={train.isPending}>
              <RefreshCw size={16} /> Entraîner Conso
            </button>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard icon={Brain} tone="green" label="Modèle production" value="Random Forest" hint={prodModel ? "Actif" : "Non entraîné"} />
        <KpiCard icon={Brain} tone="blue" label="Modèle consommation" value="Random Forest" hint="Actif" />
        <KpiCard icon={Target} tone="amber" label="Précision moyenne (R²)" value={fmt(avgR2 * 100, 1)} unit="%" />
        <KpiCard icon={Target} tone="navy" label="Modèles entraînés" value={modelList.length} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <h3 className="mb-4 font-semibold text-navy dark:text-white">Prévision de production photovoltaïque</h3>
          <ForecastChart data={toSeries(prodPred?.predictions)} />
        </div>
        <div className="card p-5">
          <h3 className="mb-4 font-semibold text-navy dark:text-white">Prévision de consommation énergétique</h3>
          <ForecastChart data={toSeries(consPred?.predictions)} />
        </div>
      </div>

      <div className="card mt-6 overflow-hidden">
        <h3 className="px-5 pt-5 font-semibold text-navy dark:text-white">Indicateurs des modèles</h3>
        <table className="mt-3 w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-500 dark:bg-white/5">
            <tr>
              <th className="px-5 py-3">Cible</th>
              <th className="px-5 py-3">Algorithme</th>
              <th className="px-5 py-3">MAE</th>
              <th className="px-5 py-3">RMSE</th>
              <th className="px-5 py-3">R²</th>
              <th className="px-5 py-3">Statut</th>
            </tr>
          </thead>
          <tbody>
            {modelList.map((m) => (
              <tr key={m.id} className="border-t border-slate-100 dark:border-white/5">
                <td className="px-5 py-2.5 font-medium">{m.target}</td>
                <td className="px-5 py-2.5 text-slate-500">{m.algorithm}</td>
                <td className="px-5 py-2.5">{fmt(m.mae, 3)}</td>
                <td className="px-5 py-2.5">{fmt(m.rmse, 3)}</td>
                <td className="px-5 py-2.5">{fmt(m.r2, 3)}</td>
                <td className="px-5 py-2.5">
                  <Badge value={m.is_active ? "VALID" : "INACTIVE"}>
                    {m.is_active ? "Actif" : "Archivé"}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
