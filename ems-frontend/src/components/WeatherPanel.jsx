import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CloudSun, RefreshCw, Sun, Thermometer, Wind } from "lucide-react";
import { forecastingApi, housesApi, weatherApi } from "../api/endpoints";
import { useAuthStore } from "../store/auth";
import { fmt } from "../utils/format";

function fmtInstant(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

/**
 * Panneau "Météo du site & panneau solaire" :
 *  - collecte à la demande des données météo (Open-Meteo) utilisées par les
 *    prévisions, avec l'heure de la dernière collecte et la cadence de la
 *    collecte automatique ;
 *  - capacité estimée du panneau (modifiable à tout moment) sur laquelle les
 *    prévisions de production sont mises à l'échelle.
 */
export default function WeatherPanel({ houseId }) {
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "ADMIN" || user?.is_superuser;
  const [feedback, setFeedback] = useState(null); // { type, msg }
  const [capacity, setCapacity] = useState("");
  const [referencePeak, setReferencePeak] = useState("");

  const { data: status } = useQuery({
    queryKey: ["weatherStatus", houseId],
    queryFn: () => weatherApi.status(houseId),
    enabled: !!houseId,
    refetchInterval: 60_000,
  });

  const { data: housesData } = useQuery({ queryKey: ["houses"], queryFn: housesApi.list });
  const houses = housesData?.results || housesData || [];
  const house = houses.find((h) => h.id === houseId);

  useEffect(() => {
    setCapacity(house?.pv_capacity_kw ?? "");
  }, [house?.id, house?.pv_capacity_kw]);

  // Modèle de production actif : porte la puissance du panneau de calibrage.
  const { data: modelsData } = useQuery({
    queryKey: ["forecastModels"],
    queryFn: forecastingApi.models,
    enabled: isAdmin,
  });
  const models = modelsData?.results || modelsData || [];
  const productionModel = models.find((m) => m.target === "production" && m.is_active);

  useEffect(() => {
    setReferencePeak(productionModel?.reference_peak_w ?? "");
  }, [productionModel?.id, productionModel?.reference_peak_w]);

  function flash(type, msg) {
    setFeedback({ type, msg });
    setTimeout(() => setFeedback(null), 4000);
  }

  const collect = useMutation({
    mutationFn: () => weatherApi.collect(houseId),
    onSuccess: () => {
      // Collecte non-bloquante côté serveur (202) : elle tourne en tâche de
      // fond. On rafraîchit le statut plusieurs fois pour afficher les
      // valeurs fraîches dès qu'elles arrivent.
      flash("success", "Collecte lancée — actualisation dans quelques secondes.");
      [3000, 6000, 9000, 12000].forEach((ms) =>
        setTimeout(() => {
          qc.invalidateQueries({ queryKey: ["weatherStatus"] });
          qc.invalidateQueries({ queryKey: ["predict"] });
        }, ms)
      );
    },
    onError: () => flash("error", "Collecte impossible. Vérifiez la connexion Internet."),
  });

  const saveCapacity = useMutation({
    mutationFn: () =>
      housesApi.patch(houseId, {
        pv_capacity_kw: capacity === "" ? null : Number(capacity),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["houses"] });
      qc.invalidateQueries({ queryKey: ["predict"] });
      flash("success", "Capacité du panneau enregistrée.");
    },
    onError: () => flash("error", "Enregistrement impossible."),
  });

  const saveReference = useMutation({
    mutationFn: () =>
      forecastingApi.updateModel(productionModel.id, {
        reference_peak_w: referencePeak === "" ? null : Number(referencePeak),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["forecastModels"] });
      qc.invalidateQueries({ queryKey: ["predict"] });
      flash("success", "Calibrage solaire enregistré.");
    },
    onError: () => flash("error", "Enregistrement impossible (réservé à l'administrateur)."),
  });

  const values = status?.values || {};
  const lastAt = fmtInstant(status?.collected_at || status?.timestamp);
  const auto = status?.auto_collect;
  const capacityChanged =
    String(capacity) !== String(house?.pv_capacity_kw ?? "");

  return (
    <div className="card mt-6 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        {/* ── Météo du site ── */}
        <div className="min-w-[260px] flex-1">
          <h3 className="mb-1 flex items-center gap-2 font-semibold text-navy dark:text-white">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-500/10">
              <CloudSun size={15} className="text-electric" strokeWidth={2.2} />
            </span>
            Météo du site
          </h3>
          <p className="text-xs text-slate-400">
            {lastAt ? `Dernière collecte : ${lastAt}` : "Aucune donnée météo collectée pour l'instant."}
            {auto?.enabled && auto?.running
              ? ` · Collecte automatique toutes les ${auto.interval_minutes} min.`
              : ""}
          </p>

          <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
            {values.temperature != null && (
              <span className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                <Thermometer size={15} className="text-solar" /> {fmt(values.temperature, 1)} °C
              </span>
            )}
            {values.irradiance != null && (
              <span className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                <Sun size={15} className="text-energy" /> {fmt(values.irradiance, 0)} W/m²
              </span>
            )}
            {values.wind_speed != null && (
              <span className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                <Wind size={15} className="text-electric" /> {fmt(values.wind_speed, 1)} m/s
              </span>
            )}
          </div>

          <button
            type="button"
            className="btn-primary mt-4 gap-2"
            onClick={() => collect.mutate()}
            disabled={collect.isPending || !houseId}
          >
            <RefreshCw size={15} className={collect.isPending ? "animate-spin" : ""} />
            {collect.isPending ? "Collecte en cours…" : "Collecter la météo maintenant"}
          </button>
        </div>

        {/* ── Panneau solaire ── */}
        <div className="min-w-[260px] flex-1">
          <h3 className="mb-1 flex items-center gap-2 font-semibold text-navy dark:text-white">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-green-50 dark:bg-green-500/10">
              <Sun size={15} className="text-energy" strokeWidth={2.2} />
            </span>
            Panneau solaire
          </h3>
          <p className="text-xs text-slate-400">
            Capacité estimée de votre installation. Les prévisions de production
            s'alignent sur cette valeur — modifiable à tout moment si votre
            configuration change.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <input
              type="number"
              step="0.05"
              min="0"
              className="input max-w-[140px]"
              placeholder="ex : 0.3"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              disabled={!house}
            />
            <span className="text-sm text-slate-400">kWc</span>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => saveCapacity.mutate()}
              disabled={!house || !capacityChanged || saveCapacity.isPending}
            >
              {saveCapacity.isPending ? "Enregistrement…" : "Enregistrer"}
            </button>
          </div>

          {isAdmin && productionModel && (
            <div className="mt-4 border-t border-slate-100 pt-3 dark:border-white/5">
              <p className="text-xs text-slate-400">
                Panneau de calibrage : puissance crête (W) du panneau physique
                dont les mesures servent de référence aux prévisions solaires.
              </p>
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="number"
                  step="5"
                  min="0"
                  className="input max-w-[140px]"
                  placeholder="ex : 250"
                  value={referencePeak}
                  onChange={(e) => setReferencePeak(e.target.value)}
                />
                <span className="text-sm text-slate-400">W</span>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => saveReference.mutate()}
                  disabled={
                    saveReference.isPending ||
                    String(referencePeak) === String(productionModel.reference_peak_w ?? "")
                  }
                >
                  {saveReference.isPending ? "Enregistrement…" : "Enregistrer"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {feedback && (
        <p
          className={`mt-3 text-sm font-medium ${
            feedback.type === "success" ? "text-energy" : "text-danger"
          }`}
        >
          {feedback.msg}
        </p>
      )}
    </div>
  );
}
