import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertOctagon,
  AlertTriangle,
  Bell,
  BellOff,
  Check,
  CheckCheck,
  Info,
  Tag,
} from "lucide-react";
import { Loading, Empty, Pagination } from "../components/ui";
import { alertsApi } from "../api/endpoints";
import { fmtDate } from "../utils/format";

const PER_PAGE = 5;

const SEV = {
  CRITICAL: { icon: AlertOctagon, border: "border-l-danger",   bg: "bg-red-50 dark:bg-red-500/5",    iconCls: "text-danger",   badge: "bg-red-100 text-danger dark:bg-red-500/15",     dot: "bg-danger",   label: "Critique"       },
  WARNING:  { icon: AlertTriangle, border: "border-l-solar",   bg: "bg-amber-50 dark:bg-amber-500/5", iconCls: "text-solar",    badge: "bg-amber-100 text-solar dark:bg-amber-500/15",  dot: "bg-solar",    label: "Avertissement"  },
  INFO:     { icon: Info,          border: "border-l-electric", bg: "bg-blue-50 dark:bg-blue-500/5",  iconCls: "text-electric", badge: "bg-blue-100 text-electric dark:bg-blue-500/15", dot: "bg-electric", label: "Information"    },
};
const DEFAULT_SEV = { icon: Bell, border: "border-l-slate-300", bg: "", iconCls: "text-slate-400", badge: "bg-slate-100 text-slate-500 dark:bg-white/5", dot: "bg-slate-400", label: "Alerte" };

const FILTERS = [
  { id: "all",      label: "Toutes",        icon: Bell          },
  { id: "unread",   label: "Non lues",      icon: BellOff       },
  { id: "CRITICAL", label: "Critique",      icon: AlertOctagon  },
  { id: "WARNING",  label: "Avertissement", icon: AlertTriangle },
  { id: "INFO",     label: "Information",   icon: Info          },
];

function sevCfg(sev) { return SEV[sev] || DEFAULT_SEV; }

export default function Alerts() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState("all");
  const [page, setPage]     = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => alertsApi.list({ page_size: 200 }),
  });

  const ack = useMutation({
    mutationFn: (id) => alertsApi.acknowledge(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const ackAll = useMutation({
    mutationFn: async () => {
      const unread = allAlerts.filter((a) => !a.is_read);
      await Promise.all(unread.map((a) => alertsApi.acknowledge(a.id)));
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  if (isLoading) return <Loading />;

  const allAlerts   = data?.results || data || [];
  const unreadCount = allAlerts.filter((a) => !a.is_read).length;
  const critCount   = allAlerts.filter((a) => a.severity === "CRITICAL").length;
  const warnCount   = allAlerts.filter((a) => a.severity === "WARNING").length;

  const counts = {
    all: allAlerts.length, unread: unreadCount,
    CRITICAL: critCount, WARNING: warnCount,
    INFO: allAlerts.filter((a) => a.severity === "INFO").length,
  };

  const filtered = allAlerts.filter((a) => {
    if (filter === "unread") return !a.is_read;
    if (filter === "all")    return true;
    return a.severity === filter;
  });

  const totalPages = Math.ceil(filtered.length / PER_PAGE);
  const safePage   = Math.min(page, Math.max(1, totalPages));
  const paged      = filtered.slice((safePage - 1) * PER_PAGE, safePage * PER_PAGE);

  function handleFilter(f) { setFilter(f); setPage(1); }

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Alertes</h1>
          <p className="mt-1 text-sm text-slate-500">
            Notifications critiques, avertissements et informations système.
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            className="btn-ghost gap-2"
            onClick={() => ackAll.mutate()}
            disabled={ackAll.isPending}
          >
            <CheckCheck size={15} strokeWidth={2.4} /> Tout acquitter
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total"          value={allAlerts.length} icon={Bell}          colorCls="text-slate-500"  bgCls="bg-slate-100 dark:bg-white/5"           />
        <StatCard label="Non lues"       value={unreadCount}      icon={BellOff}       colorCls="text-electric"   bgCls="bg-blue-50 dark:bg-blue-500/10"         />
        <StatCard label="Critiques"      value={critCount}        icon={AlertOctagon}  colorCls="text-danger"     bgCls="bg-red-50 dark:bg-red-500/10"           />
        <StatCard label="Avertissements" value={warnCount}        icon={AlertTriangle} colorCls="text-solar"      bgCls="bg-amber-50 dark:bg-amber-500/10"       />
      </div>

      {/* Filtres */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map(({ id, label, icon: Icon }) => {
          const active = filter === id;
          const count  = counts[id] ?? 0;
          return (
            <button
              key={id}
              onClick={() => handleFilter(id)}
              className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition ${
                active
                  ? "border-electric bg-electric text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:border-electric/40 hover:bg-blue-50 hover:text-electric dark:border-white/10 dark:bg-navy-panel dark:text-slate-300 dark:hover:bg-blue-500/10"
              }`}
            >
              <Icon size={14} strokeWidth={2.4} />
              {label}
              {count > 0 && (
                <span className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-xs font-bold ${
                  active ? "bg-white/20 text-white" : "bg-slate-100 text-slate-500 dark:bg-white/10 dark:text-slate-300"
                }`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Liste */}
      {filtered.length === 0 ? (
        <Empty message="Aucune alerte pour ce filtre." />
      ) : (
        <div className="card p-5">
          <div className="space-y-2">
            {paged.map((a) => {
              const cfg  = sevCfg(a.severity);
              const Icon = cfg.icon;
              return (
                <div
                  key={a.id}
                  className={`flex items-start gap-3 rounded-xl border border-l-4 p-3 transition ${cfg.border} ${
                    a.is_read ? "border-slate-100 dark:border-white/5 opacity-60" : `${cfg.bg} border-slate-100 dark:border-white/5`
                  }`}
                >
                  {/* Icône */}
                  <span className={`mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-white dark:bg-white/5`}>
                    <Icon size={15} strokeWidth={2.4} className={a.is_read ? "text-slate-400" : cfg.iconCls} />
                  </span>

                  {/* Contenu */}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      {!a.is_read && <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />}
                      <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${cfg.badge}`}>{cfg.label}</span>
                      <span className="flex items-center gap-1 text-xs text-slate-400">
                        <Tag size={10} strokeWidth={2.4} /> {a.alert_type}
                      </span>
                    </div>
                    <p className={`mt-1 line-clamp-2 text-sm leading-snug ${
                      a.is_read ? "text-slate-400" : "font-medium text-slate-800 dark:text-slate-100"
                    }`}>
                      {a.message}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">{fmtDate(a.created_at)}</p>
                  </div>

                  {/* Action */}
                  {!a.is_read ? (
                    <button
                      onClick={() => ack.mutate(a.id)}
                      disabled={ack.isPending}
                      className="flex-shrink-0 rounded-lg border border-energy/40 bg-green-50 px-2.5 py-1 text-xs font-semibold text-energy transition hover:bg-energy hover:text-white dark:bg-green-500/10"
                    >
                      <Check size={12} strokeWidth={2.8} className="inline mr-0.5" /> Acquitter
                    </button>
                  ) : (
                    <span className="flex-shrink-0 flex items-center gap-1 text-xs text-slate-400">
                      <CheckCheck size={12} strokeWidth={2.4} /> Lu
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          <Pagination page={safePage} total={filtered.length} perPage={PER_PAGE} onChange={setPage} />
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon: Icon, colorCls, bgCls }) {
  return (
    <div className="card flex items-center gap-3 p-4">
      <span className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${bgCls}`}>
        <Icon size={18} strokeWidth={2.2} className={colorCls} />
      </span>
      <div>
        <p className="text-xl font-bold text-slate-800 dark:text-white">{value}</p>
        <p className="text-xs text-slate-400">{label}</p>
      </div>
    </div>
  );
}
