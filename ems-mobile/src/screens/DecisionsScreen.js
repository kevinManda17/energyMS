import { useCallback, useEffect, useState } from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator } from "react-native";
import { Brain, RefreshCw, Zap } from "lucide-react-native";
import { Badge } from "../components/Badge";
import { Screen, PageTitle } from "../components/Screen";
import { decisionsApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt, fmtDate, ACTION_LABELS } from "../utils/format";

function titleOf(decision) {
  return decision?.decision_label || ACTION_LABELS[decision?.action] || decision?.action;
}

const LEVEL_META = {
  CRITICAL: { border: palette.danger },
  WARNING:  { border: palette.solar },
  INFO:     { border: palette.blue },
};

export default function DecisionsScreen({ navigation }) {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [triggering, setTriggering] = useState(false);

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
    setTriggering(true);
    try {
      const decision = await decisionsApi.trigger({ house: houseId });
      setRows([decision, ...rows]);
      navigation.navigate("DecisionDetail", { decision });
    } catch {
      setError("Évaluation impossible. Vérifiez la connexion.");
    } finally {
      setTriggering(false);
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <View>
          <PageTitle
            title="Décisions IA"
            subtitle={activeHouse?.name || "Aucun micro-réseau"}
          />
        </View>
        <TouchableOpacity
          style={[styles.evalBtn, triggering && styles.evalBtnLoading]}
          onPress={trigger}
          disabled={triggering}
          activeOpacity={0.8}
        >
          {triggering ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <>
              <Zap color="#fff" size={16} strokeWidth={2.6} />
              <Text style={styles.evalBtnText}>Évaluer</Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      {error ? (
        <View style={[styles.errorBox, { backgroundColor: palette.dangerLight, borderColor: "#FCA5A5" }]}>
          <Text style={{ color: palette.danger, fontSize: 13, fontWeight: "600" }}>{error}</Text>
        </View>
      ) : null}

      <FlatList
        data={rows}
        keyExtractor={(item) => String(item.id)}
        showsVerticalScrollIndicator={false}
        renderItem={({ item }) => {
          const meta = LEVEL_META[item.alert_level] || LEVEL_META.INFO;
          const confidence = (item.confidence_score || 0) * 100;
          return (
            <TouchableOpacity
              onPress={() => navigation.navigate("DecisionDetail", { decision: item })}
              activeOpacity={0.75}
            >
              <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border, borderLeftColor: meta.border }]}>
                <View style={styles.cardTop}>
                  <View style={[styles.brainIcon, { backgroundColor: palette.blueLight }]}>
                    <Brain color={palette.blue} size={15} strokeWidth={2.4} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.cardTitle, { color: t.text }]} numberOfLines={2}>
                      {titleOf(item)}
                    </Text>
                    <Text style={[styles.cardDate, { color: t.sub }]}>
                      {fmtDate(item.created_at)}
                    </Text>
                  </View>
                  <Badge value={item.alert_level || "INFO"} />
                </View>

                {(item.explanation || item.reason) ? (
                  <Text style={[styles.cardSub, { color: t.sub }]} numberOfLines={2}>
                    {item.explanation || item.reason}
                  </Text>
                ) : null}

                {/* Confidence bar */}
                <View style={styles.confidenceRow}>
                  <Text style={[styles.confidenceLabel, { color: t.sub }]}>Confiance</Text>
                  <View style={[styles.confidenceTrack, { backgroundColor: t.border }]}>
                    <View
                      style={[
                        styles.confidenceFill,
                        {
                          width: `${Math.min(confidence, 100)}%`,
                          backgroundColor: confidence >= 70 ? palette.green : confidence >= 40 ? palette.solar : palette.danger,
                        },
                      ]}
                    />
                  </View>
                  <Text style={[styles.confidencePct, { color: t.text }]}>
                    {fmt(confidence, 0)}%
                  </Text>
                </View>
              </View>
            </TouchableOpacity>
          );
        }}
        ListEmptyComponent={
          <View style={styles.emptyWrap}>
            <Brain color={t.sub} size={40} strokeWidth={1.5} />
            <Text style={[styles.emptyText, { color: t.sub }]}>
              Aucune décision.{"\n"}Appuyez sur «Évaluer» pour lancer l'analyse.
            </Text>
          </View>
        }
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  evalBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: palette.blue,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 11,
    marginTop: 8,
    minWidth: 90,
    justifyContent: "center",
  },
  evalBtnLoading: { opacity: 0.7 },
  evalBtnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
  errorBox: { borderWidth: 1, borderRadius: 10, padding: 12, marginBottom: 10 },
  card: {
    borderWidth: 1,
    borderLeftWidth: 4,
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
  },
  cardTop: { flexDirection: "row", alignItems: "flex-start", gap: 10, marginBottom: 8 },
  brainIcon: {
    width: 32,
    height: 32,
    borderRadius: 9,
    alignItems: "center",
    justifyContent: "center",
  },
  cardTitle: { fontSize: 14, fontWeight: "700", lineHeight: 20 },
  cardDate: { fontSize: 11, marginTop: 2 },
  cardSub: { fontSize: 13, lineHeight: 18, marginBottom: 10 },
  confidenceRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  confidenceLabel: { fontSize: 11, width: 58 },
  confidenceTrack: { flex: 1, height: 6, borderRadius: 3, overflow: "hidden" },
  confidenceFill: { height: "100%", borderRadius: 3 },
  confidencePct: { fontSize: 11, fontWeight: "700", width: 32, textAlign: "right" },
  emptyWrap: { alignItems: "center", marginTop: 60, gap: 14 },
  emptyText: { textAlign: "center", fontSize: 15, lineHeight: 22 },
});
