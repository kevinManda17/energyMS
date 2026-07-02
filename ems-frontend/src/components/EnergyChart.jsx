import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";

const COLORS = {
  production:  "#16A34A",
  consumption: "#2563EB",
  prevu:       "#16A34A",
  reel:        "#2563EB",
};

const GRID_STROKE = "rgba(148,163,184,0.25)";
const TICK_STYLE  = { fontSize: 11, fill: "#94A3B8" };

export function ProdConsoChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ left: -20, right: 8, top: 8 }}>
        <defs>
          <linearGradient id="gProd" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor={COLORS.production}  stopOpacity={0.35} />
            <stop offset="100%" stopColor={COLORS.production}  stopOpacity={0}    />
          </linearGradient>
          <linearGradient id="gCons" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor={COLORS.consumption} stopOpacity={0.35} />
            <stop offset="100%" stopColor={COLORS.consumption} stopOpacity={0}    />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
        <XAxis dataKey="label" tick={TICK_STYLE} axisLine={false} tickLine={false} />
        <YAxis tick={TICK_STYLE} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{
            borderRadius: "12px",
            border: "1px solid rgba(148,163,184,0.2)",
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area
          type="monotone"
          dataKey="production"
          name="Production (kW)"
          stroke={COLORS.production}
          fill="url(#gProd)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
        <Area
          type="monotone"
          dataKey="consumption"
          name="Consommation (kW)"
          stroke={COLORS.consumption}
          fill="url(#gCons)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ForecastChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ left: -20, right: 8, top: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} vertical={false} />
        <XAxis dataKey="label" tick={TICK_STYLE} axisLine={false} tickLine={false} />
        <YAxis tick={TICK_STYLE} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{
            borderRadius: "12px",
            border: "1px solid rgba(148,163,184,0.2)",
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="reel"  name="Réel"  stroke={COLORS.reel}  strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
        <Line type="monotone" dataKey="prevu" name="Prévu" stroke={COLORS.prevu} strokeWidth={2} strokeDasharray="5 4" dot={false} activeDot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
