import { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { ChartLine, Clock3, Plug, RefreshCw, Sun } from "lucide-react-native";
import { Card } from "../components/Card";
import { Badge } from "../components/Badge";
import LineChart from "../components/LineChart";
import { PageTitle, ScreenScroll } from "../components/Screen";
import { forecastingApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt } from "../utils/format";

function listFrom(res) {
  return res?.data?.results || res?.data || res?.results || res || [];
}

function fmtHour(iso) {
  return iso
    ? new Date(iso).toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "-";
}

function mergeRows(production, consumption) {
  const rows = new Map();
  production.forEach((point) => {
    rows.set(point.horizon, {
      horizon: point.horizon,
      production: point.value,
    });
  });
  consumption.forEach((point) => {
    rows.set(point.horizon, {
      ...(rows.get(point.horizon) || { horizon: point.horizon }),
      consumption: point.value,
    });
  });
  return Array.from(rows.values())
    .sort((a, b) => new Date(a.horizon) - new Date(b.horizon))
    .slice(0, 10);
}

function ForecastKpi({ icon: Icon, label, value, unit, color }) {
  const t = useTheme();
  return (
    <Card style={styles.kpi}>
      <View style={[styles.kpiIcon, { backgroundColor: color + "1A" }]}>
        <Icon color={color} size={20} />
      </View>
      <Text style={[styles.kpiLabel, { color: t.sub }]}>{label}</Text>
      <Text style={[styles.kpiValue, { color: t.text }]}>
        {value}
        {unit ? <Text style={[styles.kpiUnit, { color: t.sub }]}> {unit}</Text> : null}
      </Text>
    </Card>
  );
}

export default function ForecastingScreen() {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [models, setModels] = useState([]);
  const [production, setProduction] = useState([]);
  const [consumption, setConsumption] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const modelRes = await forecastingApi.models();
      setModels(listFrom(modelRes));

      if (!houseId) {
        setProduction([]);
        setConsumption([]);
        return;
      }

      const [prodRes, consRes] = await Promise.all([
        forecastingApi.predict({ target: "production", hours: 24, house: houseId }),
        forecastingApi.predict({ target: "consumption", hours: 24, house: houseId }),
      ]);
      setProduction(prodRes.predictions || []);
      setConsumption(consRes.predictions || []);
    } catch {
      setError("Impossible de charger les previsions.");
    } finally {
      setLoading(false);
    }
  }, [houseId]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  const rows = useMemo(
    () => mergeRows(production, consumption),
    [production, consumption]
  );
  const activeModels = models.filter((model) => model.is_active);

  return (
    <ScreenScroll>
      <View style={styles.headerRow}>
        <PageTitle
          title="Previsions horaires"
          subtitle={activeHouse?.name || "Aucun micro-reseau selectionne"}
        />
        <Pressable
          onPress={load}
          style={[styles.refreshButton, { backgroundColor: palette.blue }]}
        >
          {loading ? (
            <ActivityIndicator color={palette.white} size="small" />
          ) : (
            <RefreshCw color={palette.white} size={18} />
          )}
        </Pressable>
      </View>

      {error ? <Text style={[styles.error, { color: palette.danger }]}>{error}</Text> : null}

      <View style={styles.kpiGrid}>
        <ForecastKpi
          icon={Sun}
          label="Production dans 1h"
          value={fmt(production[0]?.value)}
          unit="kW"
          color={palette.green}
        />
        <ForecastKpi
          icon={Plug}
          label="Consommation dans 1h"
          value={fmt(consumption[0]?.value)}
          unit="kW"
          color={palette.blue}
        />
        <ForecastKpi
          icon={Clock3}
          label="Horizon"
          value="24"
          unit="h"
          color={palette.solar}
        />
        <ForecastKpi
          icon={ChartLine}
          label="Strategies actives"
          value={String(activeModels.length)}
          color={palette.navy}
        />
      </View>

      {rows.length > 0 && (
        <Card style={styles.chartCard}>
          <View style={styles.chartHeader}>
            <Text style={[styles.chartTitle, { color: t.text }]}>Courbe de prevision</Text>
            <View style={styles.legend}>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: palette.green }]} />
                <Text style={[styles.legendLabel, { color: t.sub }]}>Production</Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: palette.blue }]} />
                <Text style={[styles.legendLabel, { color: t.sub }]}>Conso.</Text>
              </View>
            </View>
          </View>
          <LineChart
            series={[
              { data: rows.map((r) => r.production ?? null), color: palette.green, label: "Production" },
              { data: rows.map((r) => r.consumption ?? null), color: palette.blue, label: "Consommation" },
            ]}
            labels={rows.map((r) => fmtHour(r.horizon))}
            height={170}
            unit="kW"
          />
        </Card>
      )}

      <Text style={[styles.section, { color: t.text }]}>Prochaines heures</Text>
      {rows.length === 0 ? (
        <Text style={[styles.empty, { color: t.sub }]}>Aucune prevision horaire.</Text>
      ) : null}
      {rows.map((row) => (
        <Card key={row.horizon} style={styles.rowCard}>
          <View>
            <Text style={[styles.rowTitle, { color: t.text }]}>{fmtHour(row.horizon)}</Text>
            <Text style={[styles.rowSub, { color: t.sub }]}>Horizon de prevision</Text>
          </View>
          <View style={styles.values}>
            <Text style={[styles.prod, { color: palette.green }]}>
              {fmt(row.production)} kW
            </Text>
            <Text style={[styles.cons, { color: palette.blue }]}>
              {fmt(row.consumption)} kW
            </Text>
          </View>
        </Card>
      ))}

      <Text style={[styles.section, { color: t.text }]}>Strategie de prevision</Text>
      {activeModels.length === 0 ? (
        <Text style={[styles.empty, { color: t.sub }]}>Aucune strategie active.</Text>
      ) : null}
      {activeModels.map((model) => (
        <Card key={model.id}>
          <View style={styles.strategyRow}>
            <View style={styles.strategyText}>
              <Text style={[styles.title, { color: t.text }]}>{model.target}</Text>
              <Text style={[styles.rowSub, { color: t.sub }]}>{model.algorithm}</Text>
              <Text style={[styles.rowSub, { color: t.sub }]}>
                Calcul horaire a partir des mesures recentes.
              </Text>
            </View>
            <Badge value="ACTIVE" />
          </View>
        </Card>
      ))}
    </ScreenScroll>
  );
}

const styles = StyleSheet.create({
  headerRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 12,
  },
  refreshButton: {
    width: 42,
    height: 42,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 2,
  },
  error: { marginBottom: 12, fontWeight: "700" },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  kpi: {
    width: "48%",
    minHeight: 124,
    marginBottom: 0,
  },
  kpiIcon: {
    width: 34,
    height: 34,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 10,
  },
  kpiLabel: { fontSize: 12, lineHeight: 16 },
  kpiValue: { marginTop: 5, fontSize: 22, fontWeight: "800" },
  kpiUnit: { fontSize: 13, fontWeight: "600" },
  chartCard: { marginBottom: 10, paddingBottom: 4 },
  chartHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  chartTitle: { fontSize: 14, fontWeight: "700" },
  legend: { flexDirection: "row", gap: 12 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 5 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendLabel: { fontSize: 11 },
  section: { fontSize: 16, fontWeight: "800", marginTop: 18, marginBottom: 8 },
  empty: { marginBottom: 12 },
  rowCard: {
    marginBottom: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
  },
  rowTitle: { fontSize: 16, fontWeight: "800" },
  rowSub: { marginTop: 3, fontSize: 12, lineHeight: 17 },
  values: { alignItems: "flex-end", gap: 4 },
  prod: { fontSize: 14, fontWeight: "800" },
  cons: { fontSize: 14, fontWeight: "800" },
  strategyRow: { flexDirection: "row", justifyContent: "space-between", gap: 12 },
  strategyText: { flex: 1 },
  title: { fontSize: 15, fontWeight: "800", marginBottom: 2 },
});
