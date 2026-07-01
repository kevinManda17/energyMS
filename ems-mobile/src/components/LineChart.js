/**
 * LineChart — graphique SVG pour React Native.
 * Utilise react-native-svg (déjà installé dans le projet).
 *
 * Props:
 *   series   Array<{ data: number[], color: string, label: string }>
 *   labels   string[]   — libellés axe X
 *   height   number     — hauteur totale (défaut 180)
 *   width    number     — largeur totale (défaut: fenêtre - 32)
 *   unit     string     — unité axe Y (défaut 'kW')
 *   showDots boolean    — afficher les points (défaut false)
 */

import React from "react";
import { Dimensions } from "react-native";
import Svg, {
  Circle,
  Defs,
  G,
  Line,
  LinearGradient,
  Path,
  Stop,
  Text as SvgText,
} from "react-native-svg";

const SCREEN_W = Dimensions.get("window").width;
const PAD = { top: 14, right: 12, bottom: 30, left: 42 };

function buildLinePath(points) {
  if (points.length === 0) return "";
  let d = `M${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;
  for (let i = 1; i < points.length; i++) {
    const p0 = points[i - 1];
    const p1 = points[i];
    const cx = ((p0.x + p1.x) / 2).toFixed(1);
    d += ` C${cx},${p0.y.toFixed(1)} ${cx},${p1.y.toFixed(1)} ${p1.x.toFixed(1)},${p1.y.toFixed(1)}`;
  }
  return d;
}

function buildAreaPath(points, chartH) {
  if (points.length === 0) return "";
  const line = buildLinePath(points);
  const last = points[points.length - 1];
  const first = points[0];
  return `${line} L${last.x.toFixed(1)},${chartH} L${first.x.toFixed(1)},${chartH} Z`;
}

export default function LineChart({
  series = [],
  labels = [],
  height = 180,
  width = SCREEN_W - 32,
  unit = "kW",
  showDots = false,
}) {
  const chartW = width - PAD.left - PAD.right;
  const chartH = height - PAD.top - PAD.bottom;

  const allValues = series.flatMap((s) => s.data).filter((v) => v != null && isFinite(v));
  const rawMin = allValues.length ? Math.min(...allValues) : 0;
  const rawMax = allValues.length ? Math.max(...allValues) : 1;
  const minVal = Math.min(0, rawMin);
  const maxVal = rawMax === minVal ? minVal + 1 : rawMax;
  const range = maxVal - minVal;

  const toY = (v) => chartH - ((v - minVal) / range) * chartH;

  const maxN = Math.max(...series.map((s) => s.data.length), 2);
  const toX = (i) => (maxN <= 1 ? chartW / 2 : (i / (maxN - 1)) * chartW);

  const Y_TICKS = 4;
  const labelStep = Math.max(1, Math.ceil(maxN / 6));

  return (
    <Svg width={width} height={height}>
      <Defs>
        {series.map((s, idx) => (
          <LinearGradient key={`grad-${idx}`} id={`grad${idx}`} x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0%" stopColor={s.color} stopOpacity="0.22" />
            <Stop offset="100%" stopColor={s.color} stopOpacity="0.01" />
          </LinearGradient>
        ))}
      </Defs>

      {/* Grid + Y labels */}
      <G x={PAD.left} y={PAD.top}>
        {Array.from({ length: Y_TICKS + 1 }, (_, i) => {
          const t = i / Y_TICKS;
          const val = minVal + t * range;
          const y = chartH - t * chartH;
          return (
            <React.Fragment key={`grid-${i}`}>
              <Line
                x1={0}
                y1={y}
                x2={chartW}
                y2={y}
                stroke="#E5E7EB"
                strokeWidth={0.8}
                strokeDasharray={i > 0 && i < Y_TICKS ? "4,3" : "0"}
              />
              <SvgText
                x={-6}
                y={y + 4}
                fontSize={9}
                fill="#9CA3AF"
                textAnchor="end"
              >
                {Math.abs(val) >= 1000
                  ? `${(val / 1000).toFixed(1)}k`
                  : val.toFixed(1)}
              </SvgText>
            </React.Fragment>
          );
        })}

        {/* Unit */}
        <SvgText x={-6} y={-4} fontSize={9} fill="#9CA3AF" textAnchor="end">
          {unit}
        </SvgText>

        {/* X labels */}
        {labels.map((lbl, i) => {
          if (i % labelStep !== 0 && i !== labels.length - 1) return null;
          return (
            <SvgText
              key={`lbl-${i}`}
              x={toX(i)}
              y={chartH + 18}
              fontSize={9}
              fill="#9CA3AF"
              textAnchor="middle"
            >
              {lbl}
            </SvgText>
          );
        })}

        {/* Series */}
        {series.map((s, idx) => {
          const pts = s.data
            .map((v, i) => ({ x: toX(i), y: v != null && isFinite(v) ? toY(v) : null }))
            .filter((p) => p.y !== null);

          if (pts.length === 0) return null;

          const areaPath = buildAreaPath(pts, chartH);
          const linePath = buildLinePath(pts);

          return (
            <G key={`series-${idx}`}>
              <Path d={areaPath} fill={`url(#grad${idx})`} />
              <Path
                d={linePath}
                fill="none"
                stroke={s.color}
                strokeWidth={2.2}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {showDots &&
                pts.map((p, i) => (
                  <Circle
                    key={`dot-${i}`}
                    cx={p.x}
                    cy={p.y}
                    r={3.5}
                    fill={s.color}
                    stroke="#fff"
                    strokeWidth={1.5}
                  />
                ))}
            </G>
          );
        })}
      </G>
    </Svg>
  );
}
