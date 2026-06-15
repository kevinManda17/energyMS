import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { Badge } from "../components/Badge";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { dataApi } from "../api/endpoints";
import { fmtDate } from "../utils/format";

export default function AlertDetailScreen({ route, navigation }) {
  const t = useTheme();
  const { alert, reload } = route.params;

  async function acknowledge() {
    try {
      await dataApi.acknowledge(alert.id);
      reload && reload();
      navigation.goBack();
    } catch {}
  }

  return (
    <View style={{ flex: 1, backgroundColor: t.bg, padding: 20 }}>
      <Badge value={alert.severity} />
      <Text style={[styles.msg, { color: t.text }]}>{alert.message}</Text>
      <Text style={{ color: t.sub, marginTop: 8 }}>
        Type : {alert.alert_type}
      </Text>
      <Text style={{ color: t.sub }}>Date : {fmtDate(alert.created_at)}</Text>
      <Text style={{ color: t.sub }}>
        Statut : {alert.is_read ? "Lue" : "Non lue"}
      </Text>

      {!alert.is_read && (
        <TouchableOpacity style={styles.button} onPress={acknowledge}>
          <Text style={{ color: "#fff", fontWeight: "700" }}>Acquitter l'alerte</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  msg: { fontSize: 18, fontWeight: "700", marginTop: 16 },
  button: {
    backgroundColor: palette.blue,
    padding: 14,
    borderRadius: 12,
    marginTop: 24,
    alignItems: "center",
  },
});
