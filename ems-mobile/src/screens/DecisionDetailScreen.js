import { ScrollView, View, Text, StyleSheet } from "react-native";
import { Activity, AlertTriangle, Battery, Brain, CheckCircle2, Cpu, Percent, Shield, Zap } from "lucide-react-native";
import { Badge } from "../components/Badge";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt, ACTION_LABELS } from "../utils/format";

function titleOf(decision) {
  return decision?.decision_label || ACTION_LABELS[decision?.action] || decision?.action;
}

const FACT_ICONS = {
  battery_soc:      { icon: Battery,     color: palette.solar,  unit: "%" },
  production:       { icon: Zap,         color: palette.green,  unit: "kW" },
  consumption:      { icon: Activity,    color: palette.blue,   unit: "kW" },
  balance:          { icon: Percent,     color: palette.slate,  unit: "kW" },
  hour:             { icon: Cpu,         color: palette.slate,  unit: "h" },
  irradiance:       { icon: Zap,         color: palette.slate,  unit: "W/m²" },
  temperature:      { icon: Activity,    color: palette.slate,  unit: "°C" },
  load_shedding:    { icon: AlertTriangle,color: palette.solar,  unit: "%" },
};

function factLabel(key) {
  const labels = {
    battery_soc: "SOC Batterie",
    production: "Production",
    consumption: "Consommation",
    balance: "Bilan",
    hour: "Heure",
    irradiance: "Irradiance",
    temperature: "Température",
    load_shedding: "Délestage",
    is_night: "Nuit",
    is_weekend: "Week-end",
    month: "Mois",
    dayofweek: "Jour",
    voltage: "Tension",
    current: "Courant",
    wind_speed: "Vent",
    humidity: "Humidité",
    pressure: "Pression",
  };
  return labels[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatFactValue(key, val) {
  if (val === null || val === undefined) return "—";
  if (typeof val === "boolean") return val ? "Oui" : "Non";
  if (typeof val === "number") return val.toFixed(3).replace(/\.?0+$/, "");
  return String(val);
}

export default function DecisionDetailScreen({ route }) {
  const t = useTheme();
  const { decision } = route.params;
  const rules = decision.fired_rules?.length ? decision.fired_rules : decision.activated_rules || [];
  const facts = decision.input_facts || decision.input_snapshot || {};
  const factEntries = Object.entries(facts);

  return (
    <ScrollView
      style={{ backgroundColor: t.bg }}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      {/* Header card */}
      <View style={[styles.headerCard, { backgroundColor: palette.blue }]}>
        <View style={styles.headerCardBg} />
        <View style={styles.decisionIconWrap}>
          <Brain color="#fff" size={26} strokeWidth={2.2} />
        </View>
        <Text style={styles.headerTitle}>{titleOf(decision)}</Text>
        <Text style={styles.headerSub} numberOfLines={3}>
          {decision.explanation || decision.reason || "Décision système automatique"}
        </Text>
        <View style={styles.headerBadges}>
          <Badge value={decision.alert_level || "INFO"} />
          <Badge value={decision.execution_mode || "RECOMMENDATION"} />
          {decision.battery_action && decision.battery_action !== "NONE" && (
            <Badge value={decision.battery_action} />
          )}
        </View>
      </View>

      {/* Scores */}
      <Text style={[styles.sectionTitle, { color: t.text }]}>Scores de décision</Text>
      <View style={styles.scoreGrid}>
        {[
          { label: "Confiance",      value: `${fmt((decision.confidence_score || 0) * 100, 0)}%`, icon: CheckCircle2, color: palette.green  },
          { label: "Risque",         value: `${fmt(decision.risk_score, 1)}%`,                    icon: AlertTriangle, color: palette.danger  },
          { label: "Délestage",      value: `${fmt(decision.shedding_level, 1)}%`,                icon: Zap,           color: palette.solar   },
          { label: "Ch. batterie",   value: `${fmt(decision.charge_battery_score, 1)}%`,          icon: Battery,       color: palette.solar   },
          { label: "Dé. batterie",   value: `${fmt(decision.discharge_battery_score, 1)}%`,       icon: Battery,       color: palette.solar   },
          { label: "Protection",     value: `${fmt(decision.protect_battery_score, 1)}%`,         icon: Shield,        color: palette.blue    },
        ].reduce((rows, score, i) => {
          if (i % 2 === 0) rows.push([score]);
          else rows[rows.length - 1].push(score);
          return rows;
        }, []).map((pair, ri) => (
          <View key={ri} style={styles.scoreRow}>
            {pair.map((s) => (
              <ScoreCard key={s.label} label={s.label} value={s.value} icon={s.icon} color={s.color} t={t} />
            ))}
            {pair.length === 1 && <View style={{ flex: 1 }} />}
          </View>
        ))}
      </View>

      {/* Fired rules */}
      <Text style={[styles.sectionTitle, { color: t.text }]}>
        Règles activées ({rules.length})
      </Text>
      {rules.length === 0 ? (
        <Text style={[styles.empty, { color: t.sub }]}>Aucune règle activée.</Text>
      ) : null}
      {rules.map((r, i) => {
        const strength = r.activation_degree ?? r.strength ?? 0;
        return (
          <View key={i} style={[styles.ruleCard, { backgroundColor: t.card, borderColor: t.border }]}>
            <View style={styles.ruleHeader}>
              <View style={[styles.ruleDot, { backgroundColor: palette.blue }]} />
              <Text style={[styles.ruleId, { color: t.text }]}>
                {r.rule_id || r.id}
              </Text>
              <View style={[styles.ruleStrengthBadge, { backgroundColor: palette.blueLight }]}>
                <Text style={{ color: palette.blue, fontSize: 11, fontWeight: "700" }}>
                  force {fmt(strength, 2)}
                </Text>
              </View>
            </View>
            <View style={[styles.ruleBar, { backgroundColor: t.border }]}>
              <View
                style={[
                  styles.ruleBarFill,
                  {
                    backgroundColor: strength > 0.6 ? palette.green : strength > 0.3 ? palette.solar : palette.blue,
                    width: `${Math.min(strength * 100, 100)}%`,
                  },
                ]}
              />
            </View>
            {(r.explanation || r.reason) ? (
              <Text style={[styles.ruleSub, { color: t.sub }]}>{r.explanation || r.reason}</Text>
            ) : null}
          </View>
        );
      })}

      {/* Input facts — as a clean list instead of JSON */}
      <Text style={[styles.sectionTitle, { color: t.text }]}>
        Faits d'entrée ({factEntries.length})
      </Text>
      {factEntries.length === 0 ? (
        <Text style={[styles.empty, { color: t.sub }]}>Aucun fait disponible.</Text>
      ) : (
        <View style={[styles.factsCard, { backgroundColor: t.card, borderColor: t.border }]}>
          {factEntries.map(([key, val], i) => {
            const meta = FACT_ICONS[key];
            const IconComp = meta?.icon || Cpu;
            const iconColor = meta?.color || palette.slate;
            const isLast = i === factEntries.length - 1;
            return (
              <View
                key={key}
                style={[
                  styles.factRow,
                  !isLast && { borderBottomWidth: 1, borderBottomColor: t.border },
                ]}
              >
                <View style={[styles.factIconWrap, { backgroundColor: iconColor + "15" }]}>
                  <IconComp color={iconColor} size={14} strokeWidth={2.4} />
                </View>
                <Text style={[styles.factKey, { color: t.sub }]}>{factLabel(key)}</Text>
                <Text style={[styles.factVal, { color: t.text }]}>
                  {formatFactValue(key, val)}
                  {meta?.unit ? <Text style={{ color: t.sub, fontSize: 11 }}> {meta.unit}</Text> : null}
                </Text>
              </View>
            );
          })}
        </View>
      )}

      <View style={{ height: 20 }} />
    </ScrollView>
  );
}

function ScoreCard({ label, value, icon: Icon, color, t }) {
  return (
    <View style={[styles.scoreCard, { backgroundColor: t.card, borderColor: t.border }]}>
      <View style={[styles.scoreIconWrap, { backgroundColor: color + "15" }]}>
        <Icon color={color} size={16} strokeWidth={2.4} />
      </View>
      <Text style={[styles.scoreLabel, { color: t.sub }]}>{label}</Text>
      <Text style={[styles.scoreValue, { color: t.text }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { paddingBottom: 28 },

  headerCard: {
    padding: 22,
    paddingTop: 28,
    overflow: "hidden",
  },
  headerCardBg: {
    position: "absolute",
    top: -50,
    right: -50,
    width: 160,
    height: 160,
    borderRadius: 80,
    backgroundColor: "rgba(255,255,255,0.07)",
  },
  decisionIconWrap: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.18)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  headerTitle: { color: "#fff", fontSize: 20, fontWeight: "800", lineHeight: 26, marginBottom: 8 },
  headerSub: { color: "rgba(255,255,255,0.8)", fontSize: 13, lineHeight: 19, marginBottom: 14 },
  headerBadges: { flexDirection: "row", flexWrap: "wrap", gap: 8 },

  sectionTitle: {
    fontSize: 15,
    fontWeight: "800",
    marginTop: 22,
    marginBottom: 10,
    paddingHorizontal: 16,
  },
  empty: { paddingHorizontal: 16, marginBottom: 8 },

  scoreGrid: {
    paddingHorizontal: 16,
    gap: 8,
  },
  scoreRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 8,
  },
  scoreCard: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
  },
  scoreIconWrap: {
    width: 28,
    height: 28,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  scoreLabel: { fontSize: 10, fontWeight: "600", marginBottom: 4 },
  scoreValue: { fontSize: 16, fontWeight: "800" },

  ruleCard: {
    marginHorizontal: 16,
    marginBottom: 8,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
  },
  ruleHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  ruleDot: { width: 8, height: 8, borderRadius: 4 },
  ruleId: { fontWeight: "700", flex: 1, fontSize: 13 },
  ruleStrengthBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  ruleBar: { height: 5, borderRadius: 3, marginBottom: 8, overflow: "hidden" },
  ruleBarFill: { height: "100%", borderRadius: 3 },
  ruleSub: { fontSize: 12, lineHeight: 17 },

  factsCard: {
    marginHorizontal: 16,
    borderWidth: 1,
    borderRadius: 12,
    overflow: "hidden",
  },
  factRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 11,
    gap: 10,
  },
  factIconWrap: {
    width: 26,
    height: 26,
    borderRadius: 7,
    alignItems: "center",
    justifyContent: "center",
  },
  factKey: { flex: 1, fontSize: 13 },
  factVal: { fontSize: 13, fontWeight: "700", textAlign: "right" },
});
