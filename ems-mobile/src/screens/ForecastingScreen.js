import { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { ChevronLeft, ChevronRight, Plug, RefreshCw, Sun } from "lucide-react-native";
import { Card } from "../components/Card";
import LineChart from "../components/LineChart";
import { PageTitle, ScreenScroll } from "../components/Screen";
import { forecastingApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt } from "../utils/format";

const STEP_MINUTES = 10;
const PAGE_SIZE = 24; // 24 x 10 min = 4h par page
const ONE_HOUR_INDEX = 60 / STEP_MINUTES - 1; // point situé à +1 h

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
  return Array.from(rows.values()).sort((a, b) => new Date(a.horizon) - new Date(b.horizon));
}

function ForecastKpi({ icon: Icon, label, value, unit, sub, color }) {
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
      {sub ? <Text style={[styles.kpiSub, { color: t.sub }]}>{sub}</Text> : null}
    </Card>
  );
}

export default function ForecastingScreen() {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [production, setProduction] = useState([]);
  const [consumption, setConsumption] = useState([]);
  // Prévisions immédiates (page 1) : alimentent les cartes "dans 10 min /
  // dans 1 h", qui ne doivent pas bouger quand on feuillette la liste.
  const [firstPoints, setFirstPoints] = useState({ production: [], consumption: [] });
  const [pagination, setPagination] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      if (!houseId) {
        setProduction([]);
        setConsumption([]);
        setFirstPoints({ production: [], consumption: [] });
        setPagination(null);
        return;
      }

      const [prodRes, consRes] = await Promise.all([
        forecastingApi.predict({
          target: "production", hours: 24, house: houseId,
          step_minutes: STEP_MINUTES, page, page_size: PAGE_SIZE,
        }),
        forecastingApi.predict({
          target: "consumption", hours: 24, house: houseId,
          step_minutes: STEP_MINUTES, page, page_size: PAGE_SIZE,
        }),
      ]);
      setProduction(prodRes.predictions || []);
      setConsumption(consRes.predictions || []);
      setPagination(prodRes.pagination || consRes.pagination || null);
      if (page === 1) {
        setFirstPoints({
          production: prodRes.predictions || [],
          consumption: consRes.predictions || [],
        });
      }
    } catch {
      setError("Impossible de charger les previsions.");
    } finally {
      setLoading(false);
    }
  }, [houseId, page]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  useEffect(() => {
    setPage(1);
  }, [houseId]);

  const rows = useMemo(
    () => mergeRows(production, consumption),
    [production, consumption]
  );
  const prod10 = firstPoints.production[0];
  const cons10 = firstPoints.consumption[0];
  const prod60 = firstPoints.production[ONE_HOUR_INDEX];
  const cons60 = firstPoints.consumption[ONE_HOUR_INDEX];

  return (
    <ScreenScroll>
      <View style={styles.headerRow}>
        <PageTitle
          title="Previsions"
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
          label={`Production dans ${STEP_MINUTES} min`}
          value={fmt(prod10?.value)}
          unit="kW"
          sub={prod10 ? `a ${fmtHour(prod10.horizon)}` : null}
          color={palette.green}
        />
        <ForecastKpi
          icon={Plug}
          label={`Consommation dans ${STEP_MINUTES} min`}
          value={fmt(cons10?.value)}
          unit="kW"
          sub={cons10 ? `a ${fmtHour(cons10.horizon)}` : null}
          color={palette.blue}
        />
        <ForecastKpi
          icon={Sun}
          label="Production dans 1 h"
          value={fmt(prod60?.value)}
          unit="kW"
          sub={prod60 ? `a ${fmtHour(prod60.horizon)}` : null}
          color={palette.solar}
        />
        <ForecastKpi
          icon={Plug}
          label="Consommation dans 1 h"
          value={fmt(cons60?.value)}
          unit="kW"
          sub={cons60 ? `a ${fmtHour(cons60.horizon)}` : null}
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

      <View style={styles.sectionHeaderRow}>
        <Text style={[styles.section, { color: t.text, marginTop: 0, marginBottom: 0 }]}>
          Prochaines previsions
        </Text>
        {pagination ? (
          <View style={styles.pager}>
            <Pressable
              onPress={() => setPage((p) => Math.max(1, p - 1))}
              disabled={!pagination.has_previous}
              style={[styles.pagerBtn, { borderColor: t.border, opacity: pagination.has_previous ? 1 : 0.35 }]}
            >
              <ChevronLeft color={t.text} size={16} />
            </Pressable>
            <Text style={[styles.pagerLabel, { color: t.sub }]}>
              {pagination.page} / {pagination.num_pages}
            </Text>
            <Pressable
              onPress={() => setPage((p) => p + 1)}
              disabled={!pagination.has_next}
              style={[styles.pagerBtn, { borderColor: t.border, opacity: pagination.has_next ? 1 : 0.35 }]}
            >
              <ChevronRight color={t.text} size={16} />
            </Pressable>
          </View>
        ) : null}
      </View>
      {rows.length === 0 ? (
        <Text style={[styles.empty, { color: t.sub }]}>Aucune prevision disponible.</Text>
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
  sectionHeaderRow: {
    marginTop: 18,
    marginBottom: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  pager: { flexDirection: "row", alignItems: "center", gap: 8 },
  pagerBtn: {
    width: 30,
    height: 30,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  pagerLabel: { fontSize: 12, fontWeight: "700", minWidth: 36, textAlign: "center" },
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
  kpiSub: { marginTop: 3, fontSize: 11 },
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
});
