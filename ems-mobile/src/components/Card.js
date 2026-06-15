import { View, Text, StyleSheet } from "react-native";
import { useTheme } from "../hooks/useTheme";

export function Card({ children, style }) {
  const t = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }, style]}>
      {children}
    </View>
  );
}

export function KpiCard({ label, value, unit, color }) {
  const t = useTheme();
  return (
    <Card style={styles.kpi}>
      <Text style={{ color: t.sub, fontSize: 12 }}>{label}</Text>
      <Text style={{ color: color || t.text, fontSize: 22, fontWeight: "700", marginTop: 4 }}>
        {value}
        {unit ? <Text style={{ fontSize: 13, color: t.sub }}> {unit}</Text> : null}
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 16,
    marginBottom: 12,
  },
  kpi: { flex: 1, minWidth: "45%", marginHorizontal: 4 },
});
