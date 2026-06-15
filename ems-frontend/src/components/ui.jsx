import { AlertTriangle, Loader2 } from "lucide-react";

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && (
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {subtitle}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Loading({ label = "Chargement…" }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-slate-400">
      <Loader2 className="animate-spin" size={18} /> {label}
    </div>
  );
}

export function ErrorState({ message = "Une erreur est survenue." }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-danger">
      <AlertTriangle size={18} /> {message}
    </div>
  );
}

export function Empty({ message = "Aucune donnée." }) {
  return (
    <div className="py-16 text-center text-sm text-slate-400">{message}</div>
  );
}

const SEVERITY = {
  CRITICAL: "bg-red-50 text-danger dark:bg-red-500/10",
  WARNING: "bg-amber-50 text-solar dark:bg-amber-500/10",
  INFO: "bg-blue-50 text-electric dark:bg-blue-500/10",
  VALID: "bg-green-50 text-energy dark:bg-green-500/10",
  ACTIVE: "bg-green-50 text-energy dark:bg-green-500/10",
  SHEDDED: "bg-amber-50 text-solar dark:bg-amber-500/10",
  FAULT: "bg-red-50 text-danger dark:bg-red-500/10",
  INACTIVE: "bg-slate-100 text-slate-500 dark:bg-white/5",
};

export function Badge({ value, children }) {
  const cls = SEVERITY[value] || "bg-slate-100 text-slate-600 dark:bg-white/5";
  return <span className={`badge ${cls}`}>{children || value}</span>;
}
