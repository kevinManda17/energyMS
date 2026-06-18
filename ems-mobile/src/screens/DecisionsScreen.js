import { useCallback, useEffect, useState } from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from "react-native";
import { Zap } from "lucide-react-native";
import { Card } from "../components/Card";
import { Badge } from "../components/Badge";
import { Screen } from "../components/Screen";
import { decisionsApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt, fmtDate, ACTION_LABELS } from "../utils/format";

function titleOf(decision) {
  return decision?.decision_label || ACTION_LABELS[decision?.action] || decision?.action;
}

export default function DecisionsScreen({ navigation }) {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!houseId) return;
    const res = await decisionsApi.list({ house: houseId, page_size: 60 });
    setRows(res.data?.results || res.data || []);
  }, [houseId]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  async function trigger() {
    if (!houseId) return;
    setError("");
    try {
      const decision = await decisionsApi.trigger({ house: houseId });
      setRows([decision, ...rows]);
      navigation.navigate("DecisionDetail", { decision });
    } catch {
      setError("Evaluation impossible.");
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <View>
          <Text style={[styles.h1, { color: t.text }]}>Decisions</Text>
          <Text style={{ color: t.sub }}>{activeHouse?.name || "Aucun micro-reseau"}</Text>
        </View>
        <TouchableOpacity style={styles.button} onPress={trigger}>
          <Zap color="#fff" size={17} strokeWidth={2.4} />
          <Text style={styles.buttonText}>Evaluer</Text>
        </TouchableOpacity>
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={rows}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <TouchableOpacity onPress={() => navigation.navigate("DecisionDetail", { decision: item })}>
            <Card>
              <View style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.title, { color: t.text }]}>{titleOf(item)}</Text>
                  <Text style={{ color: t.sub }} numberOfLines={2}>{item.explanation || item.reason}</Text>
                  <Text style={{ color: t.sub, marginTop: 6, fontSize: 12 }}>
                    {fmtDate(item.created_at)} - confiance {fmt(item.confidence_score * 100, 0)}%
                  </Text>
                </View>
                <Badge value={item.alert_level || "INFO"} />
              </View>
            </Card>
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={{ color: t.sub, textAlign: "center", marginTop: 40 }}>Aucune decision.</Text>}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
  h1: { fontSize: 28, fontWeight: "800", lineHeight: 34 },
  row: { flexDirection: "row", gap: 12, justifyContent: "space-between" },
  title: { fontWeight: "700", marginBottom: 4 },
  button: { backgroundColor: palette.blue, borderRadius: 8, paddingHorizontal: 14, paddingVertical: 10, flexDirection: "row", alignItems: "center", gap: 7 },
  buttonText: { color: "#fff", fontWeight: "700" },
  error: { color: palette.danger, marginBottom: 8 },
});
