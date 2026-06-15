const TINTS = {
  blue: "bg-blue-50 text-electric dark:bg-blue-500/10",
  green: "bg-green-50 text-energy dark:bg-green-500/10",
  amber: "bg-amber-50 text-solar dark:bg-amber-500/10",
  red: "bg-red-50 text-danger dark:bg-red-500/10",
  navy: "bg-slate-100 text-navy dark:bg-white/10 dark:text-white",
};

export default function KpiCard({ icon: Icon, label, value, unit, hint, tone = "blue" }) {
  return (
    <div className="card p-5">
      <div className="flex items-start gap-4">
        <div className={`grid h-12 w-12 place-items-center rounded-xl ${TINTS[tone]}`}>
          {Icon && <Icon size={22} />}
        </div>
        <div className="min-w-0">
          <div className="text-sm text-slate-500 dark:text-slate-400">{label}</div>
          <div className="mt-1 text-2xl font-bold text-navy dark:text-white">
            {value}
            {unit && <span className="ml-1 text-sm font-medium text-slate-400">{unit}</span>}
          </div>
          {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
        </div>
      </div>
    </div>
  );
}
