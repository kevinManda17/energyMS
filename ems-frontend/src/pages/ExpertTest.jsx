import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { FlaskConical, Play, Zap, Brain, AlertTriangle } from "lucide-react";
import { PageHeader, Loading } from "../components/ui";
import { decisionsApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";

// Interface de test du système expert : on injecte des faits à la main, on
// déclenche l'évaluation floue, et on visualise toute la chaîne (degrés
// d'appartenance -> règles activées -> décision -> lignes appliquées) sans
// attendre de vraies mesures. Sert notamment à démontrer le moteur en
// soutenance, hors ensoleillement réel.

const FACTS = [
  { key: "production_pv",       label: "Production PV",        unit: "kW", min: 0,  max: 10,  step: 0.1,  def: 0 },
  { key: "consommation",        label: "Consommation",         unit: "kW", min: 0,  max: 10,  step: 0.1,  def: 2 },
  { key: "batterie_soc",        label: "SOC batterie",         unit: "%",  min: 0,  max: 100, step: 1,    def: 50 },
  { key: "battery_temperature", label: "Température batterie",  unit: "°C", min: 0,  max: 80,  step: 1,    def: 25 },
];

const DEFAULTS = Object.fromEntries(FACTS.map((f) => [f.key, f.def]));

const ALERT_STYLES = {
  CRITICAL: "bg-red-50 text-danger dark:bg-red-500/10",
  WARNING:  "bg-amber-50 text-solar dark:bg-amber-500/10",
  INFO:     "bg-blue-50 text-electric dark:bg-blue-500/10",
  NONE:     "bg-slate-100 text-slate-500 dark:bg-white/5",
};

export default function ExpertTest() {
  const houseId = useHouseId();
  const [facts, setFacts] = useState(DEFAULTS);
  const [dataQuality, setDataQuality] = useState("GOOD");
  const [nonPriority, setNonPriority] = useState(false);
  const [apply, setApply] = useState(false);
  const [result, setResult] = useState(null);

  const evaluate = useMutation({
    mutationFn: (payload) => decisionsApi.trigger(payload),
    onSuccess: (data) => setResult(data),
  });

  function run() {
    if (!houseId) return;
    evaluate.mutate({
      house: houseId,
      ...facts,
      data_quality: dataQuality,
      non_critiques_actives: nonPriority,
      apply,
    });
  }

  return (
    <>
      <PageHeader
        title="Test du système expert"
        subtitle="Injectez des faits et observez toute la chaîne de décision floue."
        actions={
          <button
            className="btn-primary gap-2"
            onClick={run}
            disabled={!houseId || evaluate.isPending}
          >
            <Play size={16} /> {evaluate.isPending ? "Évaluation…" : "Évaluer"}
          </button>
        }
      />

      {!houseId && (
        <div className="card mb-6 p-5 text-sm text-slate-500">
          Sélectionnez d'abord un micro-réseau.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Panneau de saisie des faits */}
        <div className="card p-5">
          <div className="mb-4 flex items-center gap-2">
            <FlaskConical size={16} className="text-electric" strokeWidth={2.2} />
            <h3 className="font-semibold text-navy dark:text-white">Faits injectés</h3>
          </div>

          {FACTS.map((f) => (
            <div key={f.key} className="mb-4">
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="font-medium text-navy dark:text-white">{f.label}</span>
                <span className="font-semibold text-electric">
                  {facts[f.key]} {f.unit}
                </span>
              </div>
              <input
                type="range"
                min={f.min}
                max={f.max}
                step={f.step}
                value={facts[f.key]}
                onChange={(e) =>
                  setFacts({ ...facts, [f.key]: Number(e.target.value) })
                }
                className="w-full accent-electric"
              />
            </div>
          ))}

          <div className="mb-4">
            <span className="mb-1 block text-sm font-medium text-navy dark:text-white">
              Qualité des données
            </span>
            <div className="inline-flex overflow-hidden rounded-xl border border-slate-200 dark:border-white/10">
              {["GOOD", "PARTIAL", "BAD"].map((q) => (
                <button
                  key={q}
                  onClick={() => setDataQuality(q)}
                  className={`px-3 py-1.5 text-xs font-semibold transition ${
                    dataQuality === q
                      ? "bg-electric text-white"
                      : "text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5"
                  }`}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          <label className="mb-2 flex items-center gap-2 text-sm text-navy dark:text-white">
            <input
              type="checkbox"
              checked={nonPriority}
              onChange={(e) => setNonPriority(e.target.checked)}
              className="accent-electric"
            />
            Charges non prioritaires actives
          </label>

          <label className="flex items-center gap-2 text-sm text-navy dark:text-white">
            <input
              type="checkbox"
              checked={apply}
              onChange={(e) => setApply(e.target.checked)}
              className="accent-danger"
            />
            <span>
              Appliquer la décision aux relais
              <span className="ml-1 text-xs text-slate-400">
                (ferme la boucle : les lignes changent réellement)
              </span>
            </span>
          </label>
        </div>

        {/* Panneau de résultat */}
        <div className="card p-5">
          <div className="mb-4 flex items-center gap-2">
            <Brain size={16} className="text-electric" strokeWidth={2.2} />
            <h3 className="font-semibold text-navy dark:text-white">Décision</h3>
          </div>

          {evaluate.isPending ? (
            <Loading label="Évaluation du moteur flou…" />
          ) : evaluate.isError ? (
            <p className="text-sm text-danger">
              Échec de l'évaluation. Vérifiez la connexion au backend.
            </p>
          ) : !result ? (
            <p className="text-sm text-slate-400">
              Réglez les faits puis cliquez sur « Évaluer » pour voir la décision,
              les règles activées et les degrés d'appartenance.
            </p>
          ) : (
            <Result result={result} />
          )}
        </div>
      </div>
    </>
  );
}

function Result({ result }) {
  const rules = (result.fired_rules || [])
    .slice()
    .sort((a, b) => (b.activation_degree || 0) - (a.activation_degree || 0));

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-100 p-4 dark:border-white/5">
        <p className="text-lg font-bold text-navy dark:text-white">
          {result.decision_label || result.decision_code}
        </p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold">
          <span className="rounded-lg bg-electric/10 px-2 py-1 text-electric">
            {result.execution_mode}
          </span>
          <span className={`rounded-lg px-2 py-1 ${ALERT_STYLES[result.alert_level] || ALERT_STYLES.NONE}`}>
            <AlertTriangle size={11} className="mr-1 inline" />
            {result.alert_level}
          </span>
          <span className="rounded-lg bg-slate-100 px-2 py-1 text-slate-500 dark:bg-white/5">
            risque {Math.round(result.risk_score)} / délestage {Math.round(result.shedding_level)}
          </span>
        </div>
        {result.explanation && (
          <p className="mt-2 text-xs leading-relaxed text-slate-500">{result.explanation}</p>
        )}
      </div>

      {/* Lignes appliquées (si la boucle a été fermée) */}
      {result.applied_lines ? (
        <div className="rounded-xl border border-energy/30 bg-green-50 p-3 text-sm dark:bg-green-500/10">
          <div className="mb-1 flex items-center gap-1.5 font-semibold text-energy">
            <Zap size={14} /> Appliqué aux relais
          </div>
          <div className="flex gap-3 text-xs">
            {["line1", "line2", "line3"].map((l, i) => (
              <span key={l} className={result.applied_lines[l] ? "text-energy" : "text-danger"}>
                Ligne {i + 1} : {result.applied_lines[l] ? "ON" : "OFF"}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-100 p-3 text-xs text-slate-400 dark:border-white/5">
          Non appliqué aux relais (décision consultative, ou case « Appliquer »
          décochée).
        </div>
      )}

      {/* Règles activées */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Règles activées ({rules.length})
        </p>
        <div className="space-y-1.5">
          {rules.length === 0 && (
            <p className="text-xs text-slate-400">Aucune règle activée.</p>
          )}
          {rules.map((r) => (
            <div key={r.rule_id} className="rounded-lg border border-slate-100 p-2 dark:border-white/5">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-navy dark:text-white">{r.rule_id}</span>
                <span className="text-xs font-semibold text-electric">
                  {(r.activation_degree * 100).toFixed(0)} %
                </span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-white/5">
                <div
                  className="h-full bg-electric"
                  style={{ width: `${Math.min(100, r.activation_degree * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
