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
import { Loading, Empty } from "../components/ui";
import { alertsApi } from "../api/endpoints";
import { fmtDate } from "../utils/format";

/* ─────────────────────────────────────────────
   Configuration par sévérité
───────────────────────────────────────────── */
const SEV = {
  CRITICAL: {
    icon:   AlertOctagon,
    border: "border-l-danger",
    bg:     "bg-red-50 dark:bg-red-500/5",
    iconCls:"text-danger",
    badge:  "bg-red-100 text-danger dark:bg-red-500/15",
    dot:    "bg-danger",
    label:  "Critique",
  },
  WARNING: {
    icon:   AlertTriangle,
    border: "border-l-solar",
    bg:     "bg-amber-50 dark:bg-amber-500/5",
    iconCls:"text-solar",
    badge:  "bg-amber-100 text-solar dark:bg-amber-500/15",
    dot:    "bg-solar",
    label:  "Avertissement",
  },
  INFO: {
    icon:   Info,
    border: "border-l-electric",
    bg:     "bg-blue-50 dark:bg-blue-500/5",
    iconCls:"text-electric",
    badge:  "bg-blue-100 text-electric dark:bg-blue-500/15",
    dot:    "bg-electric",
    label:  "Information",
  },
};

const DEFAULT_SEV = {
  icon:   Bell,
  border: "border-l-slate-300",
  bg:     "",
  iconCls:"text-slate-400",
  badge:  "bg-slate-100 text-slate-500 dark:bg-white/5",
  dot:    "bg-slate-400",
  label:  "Alerte",
};

const FILTERS = [
  { id: "all",      label: "Toutes",         icon: Bell },
  { id: "unread",   label: "Non lues",       icon: BellOff },
  { id: "CRITICAL", label: "Critique",       icon: AlertOctagon },
  { id: "WARNING",  label: "Avertissement",  icon: AlertTriangle },
  { id: "INFO",     label: "Information",    icon: Info },
];

function sevCfg(sev) {
  return SEV[sev] || DEFAULT_SEV;
}

/* ─────────────────────────────────────────────
   Composant principal
───────────────────────────────────────────── */
export default function Alerts() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState("all");

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

  const allAlerts = data?.results || data || [];
  const unreadCount = allAlerts.filter((a) => !a.is_read).length;
  const critCount   = allAlerts.filter((a) => a.severity === "CRITICAL").length;
  const warnCount   = allAlerts.filter((a) => a.severity === "WARNING").length;

  const counts = {
    all:      allAlerts.length,
    unread:   unreadCount,
    CRITICAL: critCount,
    WARNING:  warnCount,
    INFO:     allAlerts.filter((a) => a.severity === "INFO").length,
  };

  const filtered = allAlerts.filter((a) => {
    if (filter === "unread")   return !a.is_read;
    if (filter === "all")      return true;
    return a.severity === filter;
  });

  return (
    <div className="space-y-6">
      {/* ── En-tête ── */}
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
            <CheckCheck size={15} strokeWidth={2.4} />
            Tout acquitter
          </button>
        )}
      </div>

      {/* ── Stats ── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          label="Total"
          value={allAlerts.length}
          icon={Bell}
          colorCls="text-slate-500"
          bgCls="bg-slate-100 dark:bg-white/5"
        />
        <StatCard
          label="Non lues"
          value={unreadCount}
          icon={BellOff}
          colorCls="text-electric"
          bgCls="bg-blue-50 dark:bg-blue-500/10"
        />
        <StatCard
          label="Critiques"
          value={critCount}
          icon={AlertOctagon}
          colorCls="text-danger"
          bgCls="bg-red-50 dark:bg-red-500/10"
        />
        <StatCard
          label="Avertissements"
          value={warnCount}
          icon={AlertTriangle}
          colorCls="text-solar"
          bgCls="bg-amber-50 dark:bg-amber-500/10"
        />
      </div>

      {/* ── Filtres ── */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map(({ id, label, icon: Icon }) => {
          const active = filter === id;
          const count  = counts[id] ?? 0;
          return (
            <button
              key={id}
              onClick={() => setFilter(id)}
              className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition ${
                active
                  ? "border-electric bg-electric text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:border-electric/40 hover:bg-blue-50 hover:text-electric dark:border-white/10 dark:bg-navy-panel dark:text-slate-300 dark:hover:bg-blue-500/10"
              }`}
            >
              <Icon size={14} strokeWidth={2.4} />
              {label}
              {count > 0 && (
                <span
                  className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-xs font-bold ${
                    active
                      ? "bg-white/20 text-white"
                      : "bg-slate-100 text-slate-500 dark:bg-white/10 dark:text-slate-300"
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── Liste ── */}
      {filtered.length === 0 ? (
        <Empty message="Aucune alerte pour ce filtre." />
      ) : (
        <div className="space-y-2">
          {filtered.map((a) => {
            const cfg = sevCfg(a.severity);
            const Icon = cfg.icon;
            return (
              <div
                key={a.id}
                className={`card flex items-start gap-4 border-l-4 p-4 transition ${cfg.border} ${
                  a.is_read ? "opacity-60" : cfg.bg
                }`}
              >
                {/* Icône sévérité */}
                <span
                  className={`mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl ${
                    a.is_read
                      ? "bg-slate-100 dark:bg-white/5"
                      : cfg.badge.replace(/text-\S+/, "").trim() + " dark:bg-white/5"
                  }`}
                >
                  <Icon
                    size={17}
                    strokeWidth={2.4}
                    className={a.is_read ? "text-slate-400" : cfg.iconCls}
                  />
                </span>

                {/* Contenu */}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Dot non-lue */}
                    {!a.is_read && (
                      <span className={`h-2 w-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
                    )}
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-bold ${cfg.badge}`}
                    >
                      {cfg.label}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-slate-400">
                      <Tag size={11} strokeWidth={2.4} />
                      {a.alert_type}
                    </span>
                  </div>

                  <p
                    className={`mt-1.5 text-sm leading-snug ${
                      a.is_read
                        ? "text-slate-400"
                        : "font-medium text-slate-800 dark:text-slate-100"
                    }`}
                  >
                    {a.message}
                  </p>

                  <p className="mt-1 text-xs text-slate-400">{fmtDate(a.created_at)}</p>
                </div>

                {/* Action acquitter */}
                {!a.is_read ? (
                  <button
                    onClick={() => ack.mutate(a.id)}
                    disabled={ack.isPending}
                    className="flex-shrink-0 rounded-xl border border-energy/40 bg-green-50 px-3 py-1.5 text-xs font-semibold text-energy transition hover:bg-energy hover:text-white dark:bg-green-500/10 dark:hover:bg-energy"
                  >
                    <Check size={13} strokeWidth={2.8} className="inline mr-1" />
                    Acquitter
                  </button>
                ) : (
                  <span className="flex-shrink-0 flex items-center gap-1 text-xs text-slate-400">
                    <CheckCheck size={13} strokeWidth={2.4} />
                    Lu
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Sous-composants
───────────────────────────────────────────── */
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
