import { useEffect, useState, useCallback } from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from "react-native";
import { Badge } from "../components/Badge";
import { useTheme } from "../hooks/useTheme";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { alertsApi } from "../api/endpoints";
import { fmtDate } from "../utils/format";
import { palette } from "../theme/colors";

const SEVERITIES = ["all", "CRITICAL", "WARNING", "INFO"];
const STATUSES = [["all", "Toutes"], ["unread", "Non lues"], ["read", "Lues"]];

export default function AlertsScreen({ navigation }) {
  const t = useTheme();
  const { houseId } = useActiveHouse();
  const [alerts, setAlerts] = useState([]);
  const [severity, setSeverity] = useState("all");
  const [status, setStatus] = useState("all");

  const load = useCallback(() => {
    const params = { page_size: 80 };
    if (houseId) params.house = houseId;
    if (severity !== "all") params.severity = severity;
    if (status !== "all") params.is_read = status === "read";
    alertsApi
      .list(params)
      .then((r) => setAlerts(r.data?.results || r.data || []))
      .catch(() => {});
  }, [houseId, severity, status]);

  useEffect(() => load(), [load]);

  return (
    <View style={{ flex: 1, backgroundColor: t.bg, padding: 12 }}>
      <Text style={[styles.h1, { color: t.text }]}>Alertes</Text>
      <View style={styles.filters}>
        {SEVERITIES.map((item) => (
          <Chip key={item} active={severity === item} label={item} onPress={() => setSeverity(item)} t={t} />
        ))}
      </View>
      <View style={styles.filters}>
        {STATUSES.map(([id, label]) => (
          <Chip key={id} active={status === id} label={label} onPress={() => setStatus(id)} t={t} />
        ))}
      </View>
      <FlatList
        data={alerts}
        keyExtractor={(i) => String(i.id)}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}
            onPress={() => navigation.navigate("AlertDetail", { alert: item, reload: load })}
          >
            <Badge value={item.severity} />
            <Text style={{ color: t.text, marginTop: 6, fontWeight: "700" }}>{item.message}</Text>
            <Text style={{ color: t.sub, fontSize: 12, marginTop: 4 }}>
              {item.alert_type} - {fmtDate(item.created_at)}
            </Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={{ color: t.sub, textAlign: "center", marginTop: 40 }}>Aucune alerte.</Text>}
      />
    </View>
  );
}

function Chip({ label, active, onPress, t }) {
  return (
    <TouchableOpacity onPress={onPress} style={[styles.chip, { borderColor: active ? palette.blue : t.border, backgroundColor: active ? palette.blue : "transparent" }]}>
      <Text style={{ color: active ? "#fff" : t.text, fontSize: 12 }}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  h1: { fontSize: 24, fontWeight: "800", marginBottom: 12, marginTop: 8 },
  card: { borderWidth: 1, borderRadius: 8, padding: 14, marginBottom: 10 },
  filters: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 8 },
  chip: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 7 },
});
