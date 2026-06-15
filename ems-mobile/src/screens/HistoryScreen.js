import { useEffect, useState } from "react";
import { View, Text, FlatList, StyleSheet } from "react-native";
import { useTheme } from "../hooks/useTheme";
import { dataApi } from "../api/endpoints";
import { fmt, fmtDate } from "../utils/format";

export default function HistoryScreen() {
  const t = useTheme();
  const [rows, setRows] = useState([]);

  useEffect(() => {
    dataApi
      .history({ ordering: "-timestamp", page_size: 80 })
      .then((r) => setRows(r.data.results || []))
      .catch(() => {});
  }, []);

  return (
    <View style={{ flex: 1, backgroundColor: t.bg, padding: 12 }}>
      <Text style={[styles.h1, { color: t.text }]}>Historique</Text>
      <FlatList
        data={rows}
        keyExtractor={(i) => String(i.id)}
        renderItem={({ item }) => (
          <View style={[styles.row, { borderColor: t.border }]}>
            <View>
              <Text style={{ color: t.text, fontWeight: "600" }}>
                {item.measurement_type}
              </Text>
              <Text style={{ color: t.sub, fontSize: 12 }}>{fmtDate(item.timestamp)}</Text>
            </View>
            <Text style={{ color: t.text, fontWeight: "700" }}>
              {fmt(item.value)} {item.unit}
            </Text>
          </View>
        )}
        ListEmptyComponent={
          <Text style={{ color: t.sub, textAlign: "center", marginTop: 40 }}>
            Aucune donnée.
          </Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  h1: { fontSize: 24, fontWeight: "800", marginBottom: 12, marginTop: 8 },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
});
