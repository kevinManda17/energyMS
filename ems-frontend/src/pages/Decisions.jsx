import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Workflow, Zap } from "lucide-react";
import { PageHeader, Loading, Empty } from "../components/ui";
import { decisionsApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";
import { fmt, fmtDate, ACTION_LABELS } from "../utils/format";

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

  if (!houseId) return <Empty message="Sélectionnez un micro-réseau." />;
  if (isLoading) return <Loading />;

  const decisions = data?.results || [];

  return (
    <>
      <PageHeader
        title="Décisions"
        subtitle="Décisions du système expert flou et règles activées."
        actions={
          <button className="btn-primary" onClick={() => trigger.mutate()} disabled={trigger.isPending}>
            <Zap size={16} /> Déclencher une décision
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <h3 className="mb-4 flex items-center gap-2 font-semibold text-navy dark:text-white">
            <Workflow size={18} /> Historique des décisions
          </h3>
          {decisions.length === 0 ? (
            <Empty message="Aucune décision." />
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
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-electric">
                      {ACTION_LABELS[d.action] || d.action}
                    </span>
                    <span className="text-xs text-slate-400">{fmtDate(d.created_at)}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">{d.reason}</p>
                  <div className="mt-2 text-xs text-slate-400">
                    Confiance : {fmt(d.confidence_score * 100, 0)}%
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card h-fit p-5">
          <h3 className="mb-3 font-semibold text-navy dark:text-white">Détail</h3>
          {selected ? (
            <>
              <div className="text-lg font-bold text-electric">
                {ACTION_LABELS[selected.action] || selected.action}
              </div>
              <p className="mt-1 text-sm text-slate-500">{selected.reason}</p>

              <div className="mt-4 text-sm font-medium">Règles activées</div>
              <ul className="mt-2 space-y-2">
                {(selected.activated_rules || []).map((r, i) => (
                  <li key={i} className="rounded-lg bg-slate-50 p-2 text-xs dark:bg-white/5">
                    <span className="font-semibold">{r.id}</span> · force {fmt(r.strength, 2)}
                    <div className="text-slate-500">{r.reason}</div>
                  </li>
                ))}
              </ul>

              <div className="mt-4 text-sm font-medium">Entrées</div>
              <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-900 p-3 text-[11px] text-slate-200">
                {JSON.stringify(selected.input_snapshot, null, 2)}
              </pre>
            </>
          ) : (
            <p className="text-sm text-slate-400">Sélectionnez une décision.</p>
          )}
        </div>
      </div>
    </>
  );
}
