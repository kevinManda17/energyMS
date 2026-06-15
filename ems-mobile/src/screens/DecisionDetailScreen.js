import { ScrollView, View, Text, StyleSheet } from "react-native";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt, ACTION_LABELS } from "../utils/format";

export default function DecisionDetailScreen({ route }) {
  const t = useTheme();
  const { decision } = route.params;

  return (
    <ScrollView style={{ backgroundColor: t.bg }} contentContainerStyle={{ padding: 20 }}>
      <Text style={{ color: palette.blue, fontSize: 22, fontWeight: "800" }}>
        {ACTION_LABELS[decision.action] || decision.action}
      </Text>
      <Text style={{ color: t.sub, marginTop: 8 }}>{decision.reason}</Text>
      <Text style={{ color: t.sub, marginTop: 8 }}>
        Confiance : {fmt(decision.confidence_score * 100, 0)}%
      </Text>

      <Text style={[styles.h2, { color: t.text }]}>Règles activées</Text>
      {(decision.activated_rules || []).map((r, i) => (
        <View key={i} style={[styles.rule, { borderColor: t.border }]}>
          <Text style={{ color: t.text, fontWeight: "600" }}>
            {r.id} · force {fmt(r.strength, 2)}
          </Text>
          <Text style={{ color: t.sub, fontSize: 13 }}>{r.reason}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  h2: { fontSize: 16, fontWeight: "700", marginTop: 20, marginBottom: 8 },
  rule: { borderWidth: 1, borderRadius: 10, padding: 10, marginBottom: 8 },
});
