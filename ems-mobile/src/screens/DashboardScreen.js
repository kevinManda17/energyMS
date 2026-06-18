import { useEffect, useState, useCallback } from "react";
import { View, Text, RefreshControl, StyleSheet, TouchableOpacity } from "react-native";
import { ChartLine, ChartNetwork, Cpu, FileText } from "lucide-react-native";
import { Card, KpiCard } from "../components/Card";
import { Badge } from "../components/Badge";
import { ScreenScroll, PageTitle } from "../components/Screen";
import { useTheme } from "../hooks/useTheme";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { palette } from "../theme/colors";
import { measurementsApi, decisionsApi, alertsApi } from "../api/endpoints";
import { fmt, ACTION_LABELS } from "../utils/format";

function byType(rows) {
  const map = {};
  (rows || []).forEach((r) => {
    map[r.measurement_type] = r.value;
  });
  return map;
}

function titleOf(decision) {
  return decision?.decision_label || ACTION_LABELS[decision?.action] || decision?.action;
}

export default function DashboardScreen({ navigation }) {
  const t = useTheme();
  const { houseId, activeHouse, offline, reload: reloadHouses } = useActiveHouse();
  const [latest, setLatest] = useState([]);
  const [decision, setDecision] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [fromCache, setFromCache] = useState(false);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!houseId) return;
    setError("");
    try {
      const m = await measurementsApi.latest(houseId);
      setLatest(m.data || []);
      setFromCache(!!m.fromCache);
    } catch {
      setError("Mesures indisponibles.");
    }
    try {
      const d = await decisionsApi.latest();
      setDecision(d.data);
    } catch {
      setDecision(null);
    }
    try {
      const a = await alertsApi.list({ house: houseId, page_size: 5 });
      setAlerts(a.data?.results || a.data || []);
    } catch {
      setAlerts([]);
    }
  }, [houseId]);

  useEffect(() => {
    load();
  }, [load]);

  async function onRefresh() {
    setRefreshing(true);
    await reloadHouses();
    await load();
    setRefreshing(false);
  }

  const m = byType(latest);
  const balance =
    m.production !== undefined && m.consumption !== undefined
      ? m.production - m.consumption
      : null;

  return (
    <ScreenScroll
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {(offline || fromCache) && (
        <View style={styles.offline}>
          <Text style={styles.offlineText}>Mode hors-ligne - donnees en cache</Text>
        </View>
      )}

      <PageTitle
        title="Tableau de bord"
        subtitle={activeHouse ? activeHouse.name : "Aucun micro-reseau selectionne"}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}

      <View style={styles.kpiRow}>
        <KpiCard label="Production" value={fmt(m.production)} unit="kW" color={palette.green} />
        <KpiCard label="Consommation" value={fmt(m.consumption)} unit="kW" color={palette.blue} />
      </View>
      <View style={styles.kpiRow}>
        <KpiCard label="Batterie" value={fmt(m.battery_soc, 0)} unit="%" color={palette.solar} />
        <KpiCard label="Tension" value={fmt(m.voltage, 0)} unit="V" color={t.text} />
      </View>
      <View style={styles.kpiRow}>
        <KpiCard label="Courant" value={fmt(m.current, 1)} unit="A" color={palette.blue} />
        <KpiCard label="Bilan" value={fmt(balance)} unit="kW" color={balance >= 0 ? palette.green : palette.danger} />
      </View>

      <Card>
        <Text style={[styles.cardTitle, { color: t.text }]}>Etat systeme</Text>
        <View style={styles.stateRow}>
          <Badge value={activeHouse?.status || "INFO"} />
          <Text style={{ color: t.sub }}>Alertes recentes: {alerts.length}</Text>
        </View>
      </Card>

      <Card>
        <Text style={[styles.cardTitle, { color: t.text }]}>Derniere decision</Text>
        {decision ? (
          <TouchableOpacity onPress={() => navigation.navigate("DecisionDetail", { decision })}>
            <Text style={{ color: palette.blue, fontSize: 17, fontWeight: "700" }}>
              {titleOf(decision)}
            </Text>
            <Text style={{ color: t.sub, marginTop: 4 }}>{decision.explanation || decision.reason}</Text>
            <View style={styles.badges}>
              <Badge value={decision.alert_level || "INFO"} />
              <Badge value={decision.execution_mode || "RECOMMENDATION"} />
            </View>
          </TouchableOpacity>
        ) : (
          <Text style={{ color: t.sub }}>Aucune decision.</Text>
        )}
      </Card>

      <View style={styles.quickGrid}>
        <QuickButton label="Micro-reseaux" icon={ChartNetwork} onPress={() => navigation.navigate("Reseaux")} />
        <QuickButton label="Equipements" icon={Cpu} onPress={() => navigation.navigate("Devices")} />
        <QuickButton label="Previsions" icon={ChartLine} onPress={() => navigation.navigate("Forecasting")} />
        <QuickButton label="Rapports" icon={FileText} onPress={() => navigation.navigate("Reports")} />
      </View>
    </ScreenScroll>
  );
}

function QuickButton({ label, icon: Icon, onPress }) {
  return (
    <TouchableOpacity style={styles.quickButton} onPress={onPress}>
      {Icon ? <Icon color="#fff" size={18} strokeWidth={2.4} /> : null}
      <Text style={styles.quickText}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  kpiRow: { flexDirection: "row" },
  cardTitle: { fontWeight: "700", marginBottom: 8 },
  stateRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 10 },
  offline: { backgroundColor: palette.solar, padding: 8, borderRadius: 8, marginBottom: 12, alignItems: "center" },
  offlineText: { color: "#fff", fontSize: 12, fontWeight: "700" },
  error: { color: palette.danger, marginBottom: 10 },
  quickGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 20 },
  quickButton: { backgroundColor: palette.blue, borderRadius: 8, padding: 12, minWidth: "48%", alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 8 },
  quickText: { color: "#fff", fontWeight: "700" },
});
