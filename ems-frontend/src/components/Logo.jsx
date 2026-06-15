import { Zap } from "lucide-react";

export default function Logo({ light = false, compact = false }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`grid h-10 w-10 place-items-center rounded-full ${
          light ? "bg-white" : "bg-electric"
        }`}
      >
        <Zap
          className={light ? "text-electric" : "text-white"}
          size={20}
          fill="currentColor"
        />
      </div>
      {!compact && (
        <div className="leading-tight">
          <div className={`text-lg font-extrabold ${light ? "text-white" : ""}`}>
            EMS
          </div>
          <div
            className={`text-[10px] uppercase tracking-wide ${
              light ? "text-slate-300" : "text-slate-400"
            }`}
          >
            Energy Management System
          </div>
        </div>
      )}
    </div>
  );
}
