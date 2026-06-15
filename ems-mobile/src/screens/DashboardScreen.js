import { useEffect, useState, useCallback } from "react";
import { ScrollView, View, Text, RefreshControl, StyleSheet, TouchableOpacity } from "react-native";
import { Card, KpiCard } from "../components/Card";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { dataApi } from "../api/endpoints";
import { fmt, ACTION_LABELS } from "../utils/format";

function byType(rows) {
  const m = {};
  (rows || []).forEach((r) => (m[r.measurement_type] = r.value));
  return m;
}

export default function DashboardScreen({ navigation }) {
  const t = useTheme();
  const [latest, setLatest] = useState([]);
  const [decision, setDecision] = useState(null);
  const [offline, setOffline] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const m = await dataApi.latest("");
      setLatest(m.data);
      setOffline(m.fromCache);
    } catch {}
    try {
      const d = await dataApi.decisionLatest();
      setDecision(d.data);
    } catch {}
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const m = byType(latest);

  return (
    <ScrollView
      style={{ backgroundColor: t.bg }}
      contentContainerStyle={{ padding: 12 }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {offline && (
        <View style={styles.offline}>
          <Text style={{ color: "#fff", fontSize: 12 }}>
            Mode hors-ligne — données en cache
          </Text>
        </View>
      )}

      <Text style={[styles.h1, { color: t.text }]}>Tableau de bord</Text>

      <View style={styles.kpiRow}>
        <KpiCard label="Production" value={fmt(m.production)} unit="kW" color={palette.green} />
        <KpiCard label="Consommation" value={fmt(m.consumption)} unit="kW" color={palette.blue} />
      </View>
      <View style={styles.kpiRow}>
        <KpiCard label="Batterie" value={fmt(m.battery_soc, 0)} unit="%" color={palette.solar} />
        <KpiCard label="Tension" value={fmt(m.voltage, 0)} unit="V" color={t.text} />
      </View>

      <Card>
        <Text style={[styles.cardTitle, { color: t.text }]}>Dernière décision</Text>
        {decision ? (
          <TouchableOpacity
            onPress={() => navigation.navigate("DecisionDetail", { decision })}
          >
            <Text style={{ color: palette.blue, fontSize: 17, fontWeight: "700" }}>
              {ACTION_LABELS[decision.action] || decision.action}
            </Text>
            <Text style={{ color: t.sub, marginTop: 4 }}>{decision.reason}</Text>
            <Text style={{ color: t.sub, fontSize: 12, marginTop: 6 }}>
              Confiance : {fmt(decision.confidence_score * 100, 0)}%
            </Text>
          </TouchableOpacity>
        ) : (
          <Text style={{ color: t.sub }}>Aucune décision.</Text>
        )}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  h1: { fontSize: 24, fontWeight: "800", marginBottom: 16, marginTop: 8 },
  kpiRow: { flexDirection: "row", marginBottom: 0 },
  cardTitle: { fontWeight: "700", marginBottom: 8 },
  offline: {
    backgroundColor: palette.solar,
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
    alignItems: "center",
  },
});
