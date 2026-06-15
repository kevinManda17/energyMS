import { useEffect, useState, useCallback } from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from "react-native";
import { Badge } from "../components/Badge";
import { useTheme } from "../hooks/useTheme";
import { dataApi } from "../api/endpoints";
import { fmtDate } from "../utils/format";

export default function AlertsScreen({ navigation }) {
  const t = useTheme();
  const [alerts, setAlerts] = useState([]);

  const load = useCallback(() => {
    dataApi
      .alerts()
      .then((r) => setAlerts(r.data.results || r.data || []))
      .catch(() => {});
  }, []);

  useEffect(() => load(), [load]);

  return (
    <View style={{ flex: 1, backgroundColor: t.bg, padding: 12 }}>
      <Text style={[styles.h1, { color: t.text }]}>Alertes</Text>
      <FlatList
        data={alerts}
        keyExtractor={(i) => String(i.id)}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}
            onPress={() => navigation.navigate("AlertDetail", { alert: item, reload: load })}
          >
            <Badge value={item.severity} />
            <Text style={{ color: t.text, marginTop: 6, fontWeight: "600" }}>
              {item.message}
            </Text>
            <Text style={{ color: t.sub, fontSize: 12, marginTop: 4 }}>
              {item.alert_type} · {fmtDate(item.created_at)}
            </Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <Text style={{ color: t.sub, textAlign: "center", marginTop: 40 }}>
            Aucune alerte.
          </Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  h1: { fontSize: 24, fontWeight: "800", marginBottom: 12, marginTop: 8 },
  card: { borderWidth: 1, borderRadius: 14, padding: 14, marginBottom: 10 },
});
