import { ScrollView, View, Text, StyleSheet } from "react-native";
import { Badge } from "../components/Badge";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt, ACTION_LABELS } from "../utils/format";

function titleOf(decision) {
  return decision?.decision_label || ACTION_LABELS[decision?.action] || decision?.action;
}

export default function DecisionDetailScreen({ route }) {
  const t = useTheme();
  const { decision } = route.params;
  const rules = decision.fired_rules?.length ? decision.fired_rules : decision.activated_rules || [];

  return (
    <ScrollView style={{ backgroundColor: t.bg }} contentContainerStyle={{ padding: 20 }}>
      <Text style={{ color: palette.blue, fontSize: 22, fontWeight: "800" }}>
        {titleOf(decision)}
      </Text>
      <Text style={{ color: t.sub, marginTop: 8 }}>{decision.explanation || decision.reason}</Text>

      <View style={styles.badges}>
        <Badge value={decision.alert_level || "INFO"} />
        <Badge value={decision.execution_mode || "RECOMMENDATION"} />
        <Badge value={decision.battery_action || "NONE"} />
      </View>

      <View style={styles.grid}>
        <Info label="Confiance" value={`${fmt(decision.confidence_score * 100, 0)}%`} t={t} />
        <Info label="Risque" value={`${fmt(decision.risk_score, 1)}%`} t={t} />
        <Info label="Delestage" value={`${fmt(decision.shedding_level, 1)}%`} t={t} />
        <Info label="Charge batterie" value={`${fmt(decision.charge_battery_score, 1)}%`} t={t} />
        <Info label="Decharge batterie" value={`${fmt(decision.discharge_battery_score, 1)}%`} t={t} />
        <Info label="Protection" value={`${fmt(decision.protect_battery_score, 1)}%`} t={t} />
      </View>

      <Text style={[styles.h2, { color: t.text }]}>Regles activees</Text>
      {rules.length === 0 ? <Text style={{ color: t.sub }}>Aucune regle activee.</Text> : null}
      {rules.map((r, i) => (
        <View key={i} style={[styles.rule, { borderColor: t.border }]}>
          <Text style={{ color: t.text, fontWeight: "700" }}>
            {r.rule_id || r.id} - force {fmt(r.activation_degree ?? r.strength, 2)}
          </Text>
          <Text style={{ color: t.sub, fontSize: 13 }}>{r.explanation || r.reason}</Text>
        </View>
      ))}

      <Text style={[styles.h2, { color: t.text }]}>Faits d'entree</Text>
      <Text style={[styles.json, { color: t.sub, borderColor: t.border }]}>
        {JSON.stringify(decision.input_facts || decision.input_snapshot || {}, null, 2)}
      </Text>
    </ScrollView>
  );
}

function Info({ label, value, t }) {
  return (
    <View style={[styles.info, { borderColor: t.border }]}>
      <Text style={{ color: t.sub, fontSize: 11 }}>{label}</Text>
      <Text style={{ color: t.text, fontWeight: "800", marginTop: 3 }}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 18 },
  info: { borderWidth: 1, borderRadius: 8, padding: 10, minWidth: "47%" },
  h2: { fontSize: 16, fontWeight: "700", marginTop: 20, marginBottom: 8 },
  rule: { borderWidth: 1, borderRadius: 8, padding: 10, marginBottom: 8 },
  json: { borderWidth: 1, borderRadius: 8, padding: 10, fontSize: 11 },
});
