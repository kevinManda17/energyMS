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
  production: "#16A34A",
  consumption: "#2563EB",
  autoconso: "#F59E0B",
  prevu: "#16A34A",
  reel: "#2563EB",
};

export function ProdConsoChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ left: -20, right: 8, top: 8 }}>
        <defs>
          <linearGradient id="gProd" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={COLORS.production} stopOpacity={0.3} />
            <stop offset="100%" stopColor={COLORS.production} stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gCons" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={COLORS.consumption} stopOpacity={0.3} />
            <stop offset="100%" stopColor={COLORS.consumption} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend />
        <Area type="monotone" dataKey="production" name="Production (kW)" stroke={COLORS.production} fill="url(#gProd)" strokeWidth={2} />
        <Area type="monotone" dataKey="consumption" name="Consommation (kW)" stroke={COLORS.consumption} fill="url(#gCons)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ForecastChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ left: -20, right: 8, top: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="reel" name="Réel" stroke={COLORS.reel} strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="prevu" name="Prévu" stroke={COLORS.prevu} strokeWidth={2} strokeDasharray="5 4" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
