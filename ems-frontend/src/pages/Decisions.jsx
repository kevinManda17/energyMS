import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Workflow, Zap } from "lucide-react";
import { PageHeader, Loading, Empty, Badge } from "../components/ui";
import { decisionsApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";
import { fmt, fmtDate, ACTION_LABELS } from "../utils/format";

function titleOf(decision) {
  return decision?.decision_label || ACTION_LABELS[decision?.action] || decision?.action;
}

export default function Decisions() {
  const qc = useQueryClient();
  const houseId = useHouseId();
  const [selected, setSelected] = useState(null);

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
    },
  });

  if (!houseId) return <Empty message="Selectionnez un micro-reseau." />;
  if (isLoading) return <Loading />;

  const decisions = data?.results || [];

  return (
    <>
      <PageHeader
        title="Decisions"
        subtitle="Evaluations du systeme expert flou et regles activees."
        actions={
          <button className="btn-primary" onClick={() => trigger.mutate()} disabled={trigger.isPending}>
            <Zap size={16} /> Declencher une evaluation
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <h3 className="mb-4 flex items-center gap-2 font-semibold text-navy dark:text-white">
            <Workflow size={18} /> Historique
          </h3>
          {decisions.length === 0 ? (
            <Empty message="Aucune decision." />
          ) : (
            <ul className="space-y-3">
              {decisions.map((d) => (
                <li
                  key={d.id}
                  onClick={() => setSelected(d)}
                  className={`cursor-pointer rounded-xl border p-4 transition hover:border-electric ${
                    selected?.id === d.id ? "border-electric bg-blue-50/50 dark:bg-electric/5" : "border-slate-100 dark:border-white/5"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-electric">{titleOf(d)}</span>
                    <span className="text-xs text-slate-400">{fmtDate(d.created_at)}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-slate-500">{d.explanation || d.reason}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <Badge value={d.alert_level || "INFO"}>{d.alert_level || "INFO"}</Badge>
                    <Badge value={d.execution_mode === "AUTOMATIC" ? "VALID" : "WARNING"}>{d.execution_mode || "RECOMMENDATION"}</Badge>
                    <span className="text-slate-400">Confiance {fmt(d.confidence_score * 100, 0)}%</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card h-fit p-5">
          <h3 className="mb-3 font-semibold text-navy dark:text-white">Detail</h3>
          {selected ? (
            <>
              <div className="text-lg font-bold text-electric">{titleOf(selected)}</div>
              <p className="mt-1 text-sm text-slate-500">{selected.explanation || selected.reason}</p>

              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <Info label="Code" value={selected.decision_code || selected.action} />
                <Info label="Mode" value={selected.execution_mode || "RECOMMENDATION"} />
                <Info label="Alerte" value={selected.alert_level || "INFO"} />
                <Info label="Batterie" value={selected.battery_action || "NONE"} />
                <Info label="Risque" value={`${fmt(selected.risk_score, 1)}%`} />
                <Info label="Delestage" value={`${fmt(selected.shedding_level, 1)}%`} />
                <Info label="Charge" value={`${fmt(selected.charge_battery_score, 1)}%`} />
                <Info label="Decharge" value={`${fmt(selected.discharge_battery_score, 1)}%`} />
              </div>

              <div className="mt-4 text-sm font-medium">Regles activees</div>
              <ul className="mt-2 space-y-2">
                {(selected.fired_rules?.length ? selected.fired_rules : selected.activated_rules || []).map((r, i) => (
                  <li key={i} className="rounded-lg bg-slate-50 p-2 text-xs dark:bg-white/5">
                    <span className="font-semibold">{r.rule_id || r.id}</span>
                    <span className="text-slate-400"> force {fmt(r.activation_degree ?? r.strength, 2)}</span>
                    <div className="text-slate-500">{r.explanation || r.reason}</div>
                  </li>
                ))}
              </ul>

              <div className="mt-4 text-sm font-medium">Faits d'entree</div>
              <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-900 p-3 text-[11px] text-slate-200">
                {JSON.stringify(selected.input_facts || selected.input_snapshot, null, 2)}
              </pre>
            </>
          ) : (
            <p className="text-sm text-slate-400">Selectionnez une decision.</p>
          )}
        </div>
      </div>
    </>
  );
}

function Info({ label, value }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-semibold text-navy dark:text-white">{value}</div>
    </div>
  );
}
