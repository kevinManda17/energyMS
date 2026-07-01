import { useCallback, useEffect, useState } from "react";
import { View, Text, FlatList, StyleSheet, TouchableOpacity } from "react-native";
import { Card } from "../components/Card";
import LineChart from "../components/LineChart";
import { Screen, PageTitle } from "../components/Screen";
import { useTheme } from "../hooks/useTheme";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { measurementsApi } from "../api/endpoints";
import { fmt, fmtDate } from "../utils/format";
import { palette } from "../theme/colors";

const TYPES = ["all", "production", "consumption", "battery_soc", "voltage", "current", "temperature"];
const PERIODS = [
  ["24h", 1],
  ["7j", 7],
  ["30j", 30],
];

const TYPE_COLOR = {
  production: palette.green,
  consumption: palette.blue,
  battery_soc: palette.solar,
  voltage: palette.navy,
  current: "#7C3AED",
  temperature: palette.danger,
};

const TYPE_UNIT = {
  production: "kW",
  consumption: "kW",
  battery_soc: "%",
  voltage: "V",
  current: "A",
  temperature: "°C",
};

function fmtHour(iso) {
  return iso
    ? new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
    : "-";
}

export default function HistoryScreen() {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [rows, setRows] = useState([]);
  const [type, setType] = useState("all");
  const [period, setPeriod] = useState(PERIODS[0]);
  const [fromCache, setFromCache] = useState(false);

  const load = useCallback(async () => {
    if (!houseId) return;
    const start = new Date(Date.now() - period[1] * 24 * 60 * 60 * 1000).toISOString();
    const params = { house: houseId, ordering: "-timestamp", page_size: 120, start };
    if (type !== "all") params.measurement_type = type;
    const res = await measurementsApi.history(params);
    setRows(res.data?.results || []);
    setFromCache(!!res.fromCache);
  }, [houseId, period, type]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  // Chart data: oldest-first slice of max 40 points for performance
  const chartRows = type !== "all" ? [...rows].reverse().slice(-40) : [];
  const chartColor = TYPE_COLOR[type] || palette.blue;
  const chartUnit = TYPE_UNIT[type] || "";

  return (
    <Screen>
      <PageTitle title="Mesures IoT" subtitle={activeHouse?.name || "Aucun micro-reseau"} />
      {fromCache ? <Text style={styles.cache}>Donnees en cache</Text> : null}

      <View style={styles.filters}>
        {TYPES.map((item) => (
          <TouchableOpacity key={item} onPress={() => setType(item)} style={[styles.chip, type === item && styles.chipActive]}>
            <Text style={{ color: type === item ? "#fff" : t.text, fontSize: 12 }}>{item}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <View style={styles.filters}>
        {PERIODS.map((item) => (
          <TouchableOpacity key={item[0]} onPress={() => setPeriod(item)} style={[styles.chip, period[0] === item[0] && styles.chipActive]}>
            <Text style={{ color: period[0] === item[0] ? "#fff" : t.text, fontSize: 12 }}>{item[0]}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {chartRows.length > 1 && (
        <Card style={styles.chartCard}>
          <View style={styles.chartHeader}>
            <Text style={[styles.chartTitle, { color: t.text }]}>
              {type} — {period[0]}
            </Text>
            <Text style={[styles.chartSub, { color: t.sub }]}>{chartRows.length} points</Text>
          </View>
          <LineChart
            series={[{ data: chartRows.map((r) => r.value), color: chartColor, label: type }]}
            labels={chartRows.map((r) => fmtHour(r.timestamp))}
            height={160}
            unit={chartUnit}
            showDots={chartRows.length <= 12}
          />
        </Card>
      )}

      <FlatList
        data={rows}
        keyExtractor={(i) => String(i.id)}
        renderItem={({ item }) => (
          <Card style={styles.measureCard}>
            <View style={styles.row}>
              <View>
                <Text style={{ color: t.text, fontWeight: "700" }}>{item.measurement_type}</Text>
                <Text style={{ color: t.sub, fontSize: 12 }}>{fmtDate(item.timestamp)}</Text>
              </View>
              <Text style={{ color: TYPE_COLOR[item.measurement_type] || t.text, fontWeight: "800" }}>
                {fmt(item.value)} {item.unit}
              </Text>
            </View>
          </Card>
        )}
        ListEmptyComponent={<Text style={{ color: t.sub, textAlign: "center", marginTop: 40 }}>Aucune mesure.</Text>}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  filters: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 8 },
  chip: { borderWidth: 1, borderColor: palette.border, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 7 },
  chipActive: { backgroundColor: palette.blue, borderColor: palette.blue },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12 },
  measureCard: { marginBottom: 8 },
  cache: { color: palette.solar, marginBottom: 8, fontWeight: "700" },
  chartCard: { marginBottom: 12, paddingBottom: 4 },
  chartHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  chartTitle: { fontSize: 13, fontWeight: "700" },
  chartSub: { fontSize: 11 },
});
