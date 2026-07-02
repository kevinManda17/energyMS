import { AlertTriangle, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";

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

export function Pagination({ page, total, perPage, onChange }) {
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  if (totalPages <= 1) return null;

  const from = (page - 1) * perPage + 1;
  const to   = Math.min(page * perPage, total);

  // Sliding window of up to 5 page numbers
  const start = Math.max(1, Math.min(page - 2, totalPages - 4));
  const end   = Math.min(totalPages, start + 4);
  const pages = [];
  for (let i = start; i <= end; i++) pages.push(i);

  return (
    <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-4 dark:border-white/5">
      <span className="text-xs text-slate-400">
        {from}–{to} sur {total}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page === 1}
          className="inline-flex items-center rounded-lg border border-slate-200 px-2 py-1.5 text-xs text-slate-500 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/10 dark:text-slate-400 dark:hover:bg-white/5"
        >
          <ChevronLeft size={13} />
        </button>
        {pages.map((p) => (
          <button
            key={p}
            onClick={() => onChange(p)}
            className={`min-w-7 rounded-lg px-2 py-1.5 text-xs font-medium transition ${
              p === page
                ? "bg-electric text-white"
                : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-white/5"
            }`}
          >
            {p}
          </button>
        ))}
        <button
          onClick={() => onChange(page + 1)}
          disabled={page === totalPages}
          className="inline-flex items-center rounded-lg border border-slate-200 px-2 py-1.5 text-xs text-slate-500 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/10 dark:text-slate-400 dark:hover:bg-white/5"
        >
          <ChevronRight size={13} />
        </button>
      </div>
    </div>
  );
}
