import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  BatteryCharging,
  Brain,
  Network,
  Plug,
  Sun,
  Thermometer,
  Zap,
} from "lucide-react";
import { PageHeader, Loading, Empty, Badge, Pagination } from "../components/ui";
import { decisionsApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";
import { fmt, fmtDate, ACTION_LABELS } from "../utils/format";

const PER_PAGE = 3;

/* ── Faits d'entrée : mapping ── */
const FACT_META = {
  battery_soc:    { label: "Batterie (SoC)",   icon: BatteryCharging, unit: "%",    color: "text-solar"     },
  production:     { label: "Production PV",     icon: Sun,             unit: "kW",   color: "text-energy"    },
  consumption:    { label: "Consommation",      icon: Plug,            unit: "kW",   color: "text-electric"  },
  voltage:        { label: "Tension réseau",    icon: Zap,             unit: "V",    color: "text-electric"  },
  current:        { label: "Courant",           icon: Activity,        unit: "A",    color: "text-slate-500" },
  grid_available: { label: "Réseau disponible", icon: Network,         unit: null,   color: "text-slate-500" },
  temperature:    { label: "Température",       icon: Thermometer,     unit: "°C",   color: "text-solar"     },
  irradiance:     { label: "Irradiance",        icon: Sun,             unit: "W/m²", color: "text-energy"    },
};

function factLabel(key) { return FACT_META[key]?.label || key.replace(/_/g, " "); }
function formatFactValue(key, val) {
  if (val == null)              return "—";
  if (typeof val === "boolean") return val ? "Oui" : "Non";
  if (typeof val === "number")  return `${val.toFixed(2)}${FACT_META[key]?.unit ? " " + FACT_META[key].unit : ""}`;
  return String(val);
}

function FactsGrid({ facts }) {
  if (!facts || Object.keys(facts).length === 0)
    return <p className="text-sm text-slate-400">Aucun fait disponible.</p>;
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {Object.entries(facts).map(([key, val]) => {
        const meta = FACT_META[key];
        const Icon = meta?.icon || Zap;
        return (
          <div key={key} className="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2.5 dark:bg-white/5">
            <span className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-white shadow-sm dark:bg-navy-panel ${meta?.color || "text-slate-400"}`}>
              <Icon size={13} strokeWidth={2.4} />
            </span>
            <div className="min-w-0">
              <p className="text-[11px] text-slate-400">{factLabel(key)}</p>
              <p className={`text-sm font-semibold ${meta?.color || "text-slate-700 dark:text-slate-200"}`}>
                {formatFactValue(key, val)}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

const LEVEL_BORDER = { CRITICAL: "border-l-danger", WARNING: "border-l-solar", INFO: "border-l-electric" };
function titleOf(d) { return d?.decision_label || ACTION_LABELS[d?.action] || d?.action; }

function ConfidenceBar({ score }) {
  const pct   = Math.min((score || 0) * 100, 100);
  const color = pct >= 70 ? "#16A34A" : pct >= 40 ? "#F59E0B" : "#DC2626";
  return (
    <div className="mt-2 space-y-1">
      <div className="flex justify-between text-xs text-slate-400">
        <span>Confiance</span>
        <span className="font-semibold">{fmt(pct, 0)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

export default function Decisions() {
  const qc      = useQueryClient();
  const houseId = useHouseId();
  const [selected, setSelected] = useState(null);
  const [page, setPage]         = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["decisions", houseId],
    queryFn: () => decisionsApi.list({ house: houseId, page_size: 50 }),
    enabled: !!houseId,
  });

  const trigger = useMutation({
    mutationFn: () => decisionsApi.trigger({ house: houseId }),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["decisions"] });
      setSelected(d);
      setPage(1);
    },
  });

  if (!houseId) return <Empty message="Sélectionnez un micro-réseau." />;
  if (isLoading) return <Loading />;

  const decisions = data?.results || [];
  const safePage  = Math.min(page, Math.max(1, Math.ceil(decisions.length / PER_PAGE)));
  const paged     = decisions.slice((safePage - 1) * PER_PAGE, safePage * PER_PAGE);

  return (
    <>
      <PageHeader
        title="Décisions IA"
        subtitle="Évaluations du système expert flou et règles activées."
        actions={
          <button
            className="btn-primary gap-2"
            onClick={() => trigger.mutate()}
            disabled={trigger.isPending}
          >
            <Brain size={16} strokeWidth={2.4} />
            {trigger.isPending ? "Évaluation…" : "Déclencher une évaluation"}
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Liste paginée */}
        <div className="card p-5 lg:col-span-2">
          <h3 className="mb-4 flex items-center gap-2 font-semibold text-navy dark:text-white">
            <Brain size={18} strokeWidth={2.2} /> Historique
          </h3>
          {decisions.length === 0 ? (
            <Empty message="Aucune décision. Lancez une évaluation pour commencer." />
          ) : (
            <>
              <ul className="space-y-2">
                {paged.map((d) => {
                  const active = selected?.id === d.id;
                  const pct    = Math.min((d.confidence_score || 0) * 100, 100);
                  const color  = pct >= 70 ? "#16A34A" : pct >= 40 ? "#F59E0B" : "#DC2626";
                  return (
                    <li
                      key={d.id}
                      onClick={() => setSelected(d)}
                      className={`cursor-pointer rounded-xl border border-l-4 p-4 transition hover:border-electric/40 ${
                        LEVEL_BORDER[d.alert_level] || "border-l-slate-300"
                      } ${active ? "border-electric bg-blue-50/50 dark:bg-electric/5" : "border-slate-100 dark:border-white/5"}`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="flex items-start gap-2">
                          <span className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-500/15">
                            <Brain size={13} className="text-purple-600 dark:text-purple-400" />
                          </span>
                          <span className="font-semibold text-electric line-clamp-1">{titleOf(d)}</span>
                        </div>
                        <span className="text-xs text-slate-400 flex-shrink-0">{fmtDate(d.created_at)}</span>
                      </div>
                      <p className="mt-1 line-clamp-2 text-sm text-slate-500">{d.explanation || d.reason}</p>
                      <div className="mt-2 flex items-center gap-3">
                        <div className="flex-1 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10">
                          <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
                        </div>
                        <span className="text-xs font-semibold text-slate-500 flex-shrink-0">{fmt(pct, 0)}%</span>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Badge value={d.alert_level || "INFO"}>{d.alert_level || "INFO"}</Badge>
                        <Badge value={d.execution_mode === "AUTOMATIC" ? "VALID" : "WARNING"}>
                          {d.execution_mode || "RECOMMENDATION"}
                        </Badge>
                      </div>
                    </li>
                  );
                })}
              </ul>
              <Pagination page={safePage} total={decisions.length} perPage={PER_PAGE} onChange={setPage} />
            </>
          )}
        </div>

        {/* Panneau détail */}
        <div className="card h-fit p-5">
          <h3 className="mb-4 font-semibold text-navy dark:text-white">Détail</h3>
          {selected ? (
            <div className="space-y-5">
              <div>
                <p className="text-lg font-bold leading-snug text-electric line-clamp-2">{titleOf(selected)}</p>
                <p className="mt-1 line-clamp-3 text-sm text-slate-500">{selected.explanation || selected.reason}</p>
                <ConfidenceBar score={selected.confidence_score} />
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm">
                {[
                  ["Code",      selected.decision_code || selected.action],
                  ["Mode",      selected.execution_mode || "RECOMMENDATION"],
                  ["Alerte",    selected.alert_level || "INFO"],
                  ["Batterie",  selected.battery_action || "NONE"],
                  ["Risque",    `${fmt(selected.risk_score, 1)}%`],
                  ["Délestage", `${fmt(selected.shedding_level, 1)}%`],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-lg bg-slate-50 p-2.5 dark:bg-white/5">
                    <p className="text-[11px] text-slate-400">{label}</p>
                    <p className="font-semibold text-navy dark:text-white truncate">{value}</p>
                  </div>
                ))}
              </div>

              {((selected.fired_rules?.length ? selected.fired_rules : selected.activated_rules) || []).length > 0 && (
                <div>
                  <p className="mb-2 text-sm font-semibold text-navy dark:text-white">Règles activées</p>
                  <ul className="space-y-2">
                    {(selected.fired_rules?.length ? selected.fired_rules : selected.activated_rules || []).map((r, i) => {
                      const strength = r.activation_degree ?? r.strength ?? 0;
                      const pct      = Math.min(strength * 100, 100);
                      return (
                        <li key={i} className="rounded-lg border border-slate-100 p-2.5 dark:border-white/5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-semibold text-slate-700 dark:text-slate-200 truncate">{r.rule_id || r.id}</span>
                            <span className="text-xs text-slate-400 flex-shrink-0">{fmt(strength, 2)}</span>
                          </div>
                          <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10">
                            <div className="h-full rounded-full bg-energy" style={{ width: `${pct}%` }} />
                          </div>
                          {(r.explanation || r.reason) && (
                            <p className="mt-1 line-clamp-2 text-[11px] text-slate-400">{r.explanation || r.reason}</p>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}

              {(selected.input_facts || selected.input_snapshot) && (
                <div>
                  <p className="mb-2 text-sm font-semibold text-navy dark:text-white">Faits d'entrée</p>
                  <FactsGrid facts={selected.input_facts || selected.input_snapshot} />
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-400">Sélectionnez une décision pour voir le détail.</p>
          )}
        </div>
      </div>
    </>
  );
}
