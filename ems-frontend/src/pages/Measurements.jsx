import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, Battery, Check, Zap, Sun } from "lucide-react";
import { PageHeader, Loading, Empty, Pagination } from "../components/ui";
import { ProdConsoChart } from "../components/EnergyChart";
import { measurementsApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";
import { fmt, fmtDate, fmtTime } from "../utils/format";

const FILTERS = [
  { id: "",            label: "Tous",           icon: Activity, color: "text-slate-500"  },
  { id: "production",  label: "Production",     icon: Sun,      color: "text-energy"     },
  { id: "consumption", label: "Consommation",   icon: Zap,      color: "text-electric"   },
  { id: "battery_soc", label: "Batterie (SoC)", icon: Battery,  color: "text-solar"      },
  { id: "voltage",     label: "Tension",        icon: Zap,      color: "text-slate-500"  },
];

const TYPE_STYLE = {
  production:  { badge: "bg-green-50 text-energy dark:bg-green-500/10",   dot: "bg-energy"   },
  consumption: { badge: "bg-blue-50 text-electric dark:bg-blue-500/10",   dot: "bg-electric" },
  battery_soc: { badge: "bg-amber-50 text-solar dark:bg-amber-500/10",    dot: "bg-solar"    },
  voltage:     { badge: "bg-slate-100 text-slate-600 dark:bg-white/5",    dot: "bg-slate-400"},
  current:     { badge: "bg-slate-100 text-slate-600 dark:bg-white/5",    dot: "bg-slate-400"},
};

function buildSeries(rows) {
  const acc = {};
  rows.forEach((m) => {
    const label = fmtTime(m.timestamp);
    acc[label] = acc[label] || { label };
    if (m.measurement_type === "production")  acc[label].production  = m.value;
    if (m.measurement_type === "consumption") acc[label].consumption = m.value;
  });
  return Object.values(acc).reverse();
}

const TABLE_PER_PAGE = 10;

export default function Measurements() {
  const houseId = useHouseId();
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["measurements", houseId, type],
    queryFn: () =>
      measurementsApi.history({
        house: houseId,
        measurement_type: type || undefined,
        ordering: "-timestamp",
        page_size: 100,
      }),
    enabled: !!houseId,
  });

  if (!houseId) return <Empty message="Sélectionnez un micro-réseau." />;
  if (isLoading)  return <Loading />;

  const rows     = data?.results || [];
  const safePage = Math.min(page, Math.max(1, Math.ceil(rows.length / TABLE_PER_PAGE)));
  const paged    = rows.slice((safePage - 1) * TABLE_PER_PAGE, safePage * TABLE_PER_PAGE);

  return (
    <>
      <PageHeader
        title="Mesures IoT"
        subtitle="Données collectées depuis les capteurs via MQTT."
      />

      {/* Filtres chips */}
      <div className="mb-5 flex flex-wrap gap-2">
        {FILTERS.map(({ id, label, icon: Icon, color }) => {
          const active = type === id;
          return (
            <button
              key={id}
              onClick={() => { setType(id); setPage(1); }}
              className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition ${
                active
                  ? "border-electric bg-electric text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:border-electric/40 hover:bg-blue-50 hover:text-electric dark:border-white/10 dark:bg-navy-panel dark:text-slate-300 dark:hover:bg-blue-500/10"
              }`}
            >
              <Icon size={14} strokeWidth={2.4} className={active ? "text-white" : color} />
              {label}
              {active && <Check size={12} strokeWidth={2.8} />}
            </button>
          );
        })}
      </div>

      {/* Graphique */}
      <div className="card mb-6 p-5">
        <h3 className="mb-4 font-semibold text-navy dark:text-white">
          {type ? FILTERS.find((f) => f.id === type)?.label : "Production & Consommation"}
        </h3>
        <ProdConsoChart data={buildSeries(rows)} />
      </div>

      {/* Tableau */}
      <div className="card overflow-hidden">
        <div className="px-5 pt-5 pb-3 flex items-center justify-between">
          <h3 className="font-semibold text-navy dark:text-white">
            Historique
          </h3>
          <span className="text-xs text-slate-400">{rows.length} mesure{rows.length !== 1 ? "s" : ""}</span>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-500 dark:bg-white/5">
            <tr>
              <th className="px-5 py-3 font-medium">Horodatage</th>
              <th className="px-5 py-3 font-medium">Type</th>
              <th className="px-5 py-3 font-medium">Valeur</th>
              <th className="px-5 py-3 font-medium">Unité</th>
            </tr>
          </thead>
          <tbody>
            {paged.map((m) => {
              const s = TYPE_STYLE[m.measurement_type] || TYPE_STYLE.voltage;
              return (
                <tr key={m.id} className="border-t border-slate-100 dark:border-white/5">
                  <td className="px-5 py-2.5 text-slate-500">{fmtDate(m.timestamp)}</td>
                  <td className="px-5 py-2.5">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${s.badge}`}>
                      <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${s.dot}`} />
                      {m.measurement_type}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 font-semibold text-navy dark:text-white">{fmt(m.value)}</td>
                  <td className="px-5 py-2.5 text-slate-400">{m.unit || "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows.length === 0 && <Empty message="Aucune mesure pour ce filtre." />}
        {rows.length > TABLE_PER_PAGE && (
          <div className="px-5 pb-4">
            <Pagination page={safePage} total={rows.length} perPage={TABLE_PER_PAGE} onChange={(p) => { setPage(p); }} />
          </div>
        )}
      </div>
    </>
  );
}
