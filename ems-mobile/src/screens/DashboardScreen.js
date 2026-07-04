import { useEffect, useState, useCallback } from "react";
import { View, Text, RefreshControl, StyleSheet, TouchableOpacity } from "react-native";
import {
  Activity,
  AlertTriangle,
  Battery,
  BarChart2,
  Brain,
  ChevronRight,
  Network,
  RefreshCw,
  Zap,
} from "lucide-react-native";
import { Badge } from "../components/Badge";
import { ScreenScroll, PageTitle } from "../components/Screen";
import { useTheme } from "../hooks/useTheme";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { palette } from "../theme/colors";
import { measurementsApi, decisionsApi, alertsApi } from "../api/endpoints";
import { fmt, ACTION_LABELS } from "../utils/format";

function byType(rows) {
  const map = {};
  (rows || []).forEach((r) => {
    map[r.measurement_type] = r.value;
  });
  return map;
}

function titleOf(decision) {
  return decision?.decision_label || ACTION_LABELS[decision?.action] || decision?.action;
}

export default function DashboardScreen({ navigation }) {
  const t = useTheme();
  const { houseId, activeHouse, offline, reload: reloadHouses } = useActiveHouse();
  const [latest, setLatest] = useState([]);
  const [decision, setDecision] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [fromCache, setFromCache] = useState(false);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!houseId) return;
    setError("");
    try {
      const m = await measurementsApi.latest(houseId);
      setLatest(m.data || []);
      setFromCache(!!m.fromCache);
    } catch {
      setError("Mesures indisponibles.");
    }
    try {
      const d = await decisionsApi.latest();
      setDecision(d.data);
    } catch {
      setDecision(null);
    }
    try {
      const a = await alertsApi.list({ house: houseId, page_size: 5 });
      setAlerts(a.data?.results || a.data || []);
    } catch {
      setAlerts([]);
    }
  }, [houseId]);

  useEffect(() => {
    load();
  }, [load]);

  async function onRefresh() {
    setRefreshing(true);
    await reloadHouses();
    await load();
    setRefreshing(false);
  }

  const m = byType(latest);
  const balance =
    m.production !== undefined && m.consumption !== undefined
      ? m.production - m.consumption
      : null;
  const unreadAlerts = alerts.filter((a) => !a.is_read).length;

  return (
    <ScreenScroll
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={palette.blue} />}
    >
      {(offline || fromCache) && (
        <View style={[styles.offlineBanner, { backgroundColor: palette.solarLight, borderColor: "#FCD34D" }]}>
          <RefreshCw color="#B45309" size={13} strokeWidth={2.4} />
          <Text style={styles.offlineText}>Mode hors-ligne · données en cache</Text>
        </View>
      )}

      <View style={styles.titleRow}>
        <PageTitle
          title="Tableau de bord"
          subtitle={activeHouse ? activeHouse.name : "Sélectionnez un micro-réseau"}
        />
        {unreadAlerts > 0 && (
          <TouchableOpacity
            style={styles.alertPill}
            onPress={() => navigation.navigate("Alertes")}
          >
            <AlertTriangle color={palette.danger} size={13} strokeWidth={2.4} />
            <Text style={styles.alertPillText}>{unreadAlerts}</Text>
          </TouchableOpacity>
        )}
      </View>

      {error ? (
        <View style={[styles.errorBox, { backgroundColor: palette.dangerLight, borderColor: "#FCA5A5" }]}>
          <Text style={{ color: palette.danger, fontSize: 13 }}>{error}</Text>
        </View>
      ) : null}

      {/* KPI grid */}
      <View style={styles.kpiGrid}>
        <KpiTile
          icon={Zap}
          label="Production"
          value={fmt(m.production)}
          unit="kW"
          color={palette.green}
          bg={palette.greenLight}
        />
        <KpiTile
          icon={Activity}
          label="Consommation"
          value={fmt(m.consumption)}
          unit="kW"
          color={palette.blue}
          bg={palette.blueLight}
        />
        <KpiTile
          icon={Battery}
          label="Batterie"
          value={fmt(m.battery_soc, 0)}
          unit="%"
          color={palette.solar}
          bg={palette.solarLight}
        />
        <KpiTile
          icon={BarChart2}
          label="Bilan"
          value={balance != null ? fmt(balance) : "—"}
          unit="kW"
          color={balance != null && balance >= 0 ? palette.green : palette.danger}
          bg={balance != null && balance >= 0 ? palette.greenLight : palette.dangerLight}
        />
      </View>

      {/* Energy balance bars */}
      <EnergyBalanceCard
        production={m.production}
        consumption={m.consumption}
        soc={m.battery_soc}
        t={t}
      />

      {/* Latest decision */}
      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <View style={styles.cardHeader}>
          <View style={[styles.cardIconWrap, { backgroundColor: palette.blueLight }]}>
            <Brain color={palette.blue} size={16} strokeWidth={2.4} />
          </View>
          <Text style={[styles.cardTitle, { color: t.text }]}>Dernière décision IA</Text>
        </View>
        {decision ? (
          <TouchableOpacity
            onPress={() => navigation.navigate("DecisionDetail", { decision })}
            activeOpacity={0.75}
          >
            <Text style={[styles.decisionTitle, { color: palette.blue }]} numberOfLines={2}>
              {titleOf(decision)}
            </Text>
            {(decision.explanation || decision.reason) ? (
              <Text style={[styles.decisionSub, { color: t.sub }]} numberOfLines={2}>
                {decision.explanation || decision.reason}
              </Text>
            ) : null}
            <View style={styles.decisionFooter}>
              <View style={styles.decisionBadges}>
                <Badge value={decision.alert_level || "INFO"} />
                <Badge value={decision.execution_mode || "RECOMMENDATION"} />
              </View>
              <ChevronRight color={t.sub} size={18} strokeWidth={2} />
            </View>
          </TouchableOpacity>
        ) : (
          <Text style={[styles.emptyText, { color: t.sub }]}>Aucune décision disponible.</Text>
        )}
      </View>

      {/* System status */}
      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <View style={styles.cardHeader}>
          <View style={[styles.cardIconWrap, { backgroundColor: palette.blueLight }]}>
            <Network color={palette.blue} size={16} strokeWidth={2.4} />
          </View>
          <Text style={[styles.cardTitle, { color: t.text }]}>État système</Text>
        </View>
        <View style={styles.statusRow}>
          <Badge value={activeHouse?.status || "INFO"} />
          <Text style={{ color: t.sub, fontSize: 13 }}>
            {unreadAlerts > 0
              ? `${unreadAlerts} alerte${unreadAlerts > 1 ? "s" : ""} non lue${unreadAlerts > 1 ? "s" : ""}`
              : "Aucune alerte active"}
          </Text>
        </View>
        <View style={[styles.voltRow, { borderTopColor: t.border }]}>
          <InfoChip label="Tension" value={`${fmt(m.voltage, 0)} V`} t={t} />
          <InfoChip label="Courant" value={`${fmt(m.current, 1)} A`} t={t} />
        </View>
      </View>

      {/* Quick actions */}
      <Text style={[styles.sectionLabel, { color: t.sub }]}>Accès rapide</Text>
      <View style={styles.quickGrid}>
        <QuickButton label="Micro-réseaux" icon={Network} onPress={() => navigation.navigate("Reseaux")} />
        <QuickButton label="Mesures IoT" icon={BarChart2} onPress={() => navigation.navigate("Mesures")} />
        <QuickButton label="Prévisions" icon={Zap} onPress={() => navigation.navigate("Forecasting")} />
        <QuickButton label="Décisions IA" icon={Brain} onPress={() => navigation.navigate("Decisions")} />
      </View>
    </ScreenScroll>
  );
}

function KpiTile({ icon: Icon, label, value, unit, color, bg }) {
  const t = useTheme();
  return (
    <View style={[styles.kpiTile, { backgroundColor: t.card, borderColor: t.border }]}>
      <View style={[styles.kpiIconWrap, { backgroundColor: bg }]}>
        <Icon color={color} size={18} strokeWidth={2.4} />
      </View>
      <Text style={[styles.kpiLabel, { color: t.sub }]}>{label}</Text>
      <Text style={[styles.kpiValue, { color }]}>
        {value}
        {unit ? <Text style={[styles.kpiUnit, { color: t.sub }]}> {unit}</Text> : null}
      </Text>
    </View>
  );
}

function EnergyBalanceCard({ production, consumption, soc, t }) {
  const total = Math.max(production || 0, consumption || 0, 0.01);
  const bars = [
    { label: "Production", value: production, color: palette.green, bg: palette.greenLight, max: total, unit: " kW" },
    { label: "Consommation", value: consumption, color: palette.blue, bg: palette.blueLight, max: total, unit: " kW" },
    { label: "Batterie", value: soc, color: palette.solar, bg: palette.solarLight, max: 100, unit: "%" },
  ];
  return (
    <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
      <View style={styles.cardHeader}>
        <View style={[styles.cardIconWrap, { backgroundColor: palette.blueLight }]}>
          <Activity color={palette.blue} size={16} strokeWidth={2.4} />
        </View>
        <Text style={[styles.cardTitle, { color: t.text }]}>Bilan énergétique</Text>
      </View>
      {bars.map((bar) => {
        const pct = Math.min(Math.max(((bar.value || 0) / bar.max) * 100, 0), 100);
        return (
          <View key={bar.label} style={styles.balanceRow}>
            <Text style={[styles.balanceLabel, { color: bar.color }]}>{bar.label}</Text>
            <View style={[styles.balanceTrack, { backgroundColor: bar.bg }]}>
              <View style={[styles.balanceFill, { width: `${pct}%`, backgroundColor: bar.color }]} />
            </View>
            <Text style={[styles.balanceVal, { color: bar.color }]}>
              {bar.value != null ? `${Number(bar.value).toFixed(1)}${bar.unit}` : "—"}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

function QuickButton({ label, icon: Icon, onPress }) {
  const t = useTheme();
  return (
    <TouchableOpacity
      style={[styles.quickBtn, { backgroundColor: t.card, borderColor: t.border }]}
      onPress={onPress}
      activeOpacity={0.75}
    >
      <View style={styles.quickIconWrap}>
        <Icon color={palette.blue} size={18} strokeWidth={2.4} />
      </View>
      <Text style={[styles.quickText, { color: t.text }]}>{label}</Text>
    </TouchableOpacity>
  );
}

function InfoChip({ label, value, t }) {
  return (
    <View style={[styles.infoChip, { backgroundColor: t.bg }]}>
      <Text style={{ color: t.sub, fontSize: 11 }}>{label}</Text>
      <Text style={{ color: t.text, fontSize: 13, fontWeight: "700" }}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  offlineBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginBottom: 12,
  },
  offlineText: { color: "#B45309", fontSize: 13, fontWeight: "600" },
  titleRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  alertPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: palette.dangerLight,
    borderWidth: 1,
    borderColor: "#FCA5A5",
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
    marginTop: 10,
  },
  alertPillText: { color: palette.danger, fontWeight: "800", fontSize: 12 },
  errorBox: { borderWidth: 1, borderRadius: 10, padding: 12, marginBottom: 10 },
  kpiGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 12 },
  kpiTile: {
    flex: 1,
    minWidth: "47%",
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
  },
  kpiIconWrap: { width: 36, height: 36, borderRadius: 10, alignItems: "center", justifyContent: "center", marginBottom: 10 },
  kpiLabel: { fontSize: 12, lineHeight: 16, marginBottom: 4 },
  kpiValue: { fontSize: 22, fontWeight: "800" },
  kpiUnit: { fontSize: 12, fontWeight: "600" },
  card: { borderWidth: 1, borderRadius: 14, padding: 14, marginBottom: 12 },
  cardHeader: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 12 },
  cardIconWrap: { width: 30, height: 30, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  cardTitle: { fontWeight: "800", fontSize: 14 },
  balanceRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  balanceLabel: { fontSize: 11, fontWeight: "700", width: 82 },
  balanceTrack: { flex: 1, height: 10, borderRadius: 5, overflow: "hidden" },
  balanceFill: { height: "100%", borderRadius: 5 },
  balanceVal: { fontSize: 11, fontWeight: "700", width: 58, textAlign: "right" },
  decisionTitle: { fontSize: 15, fontWeight: "800", lineHeight: 21, marginBottom: 6 },
  decisionSub: { fontSize: 13, lineHeight: 18, marginBottom: 10 },
  decisionFooter: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  decisionBadges: { flexDirection: "row", gap: 6, flexWrap: "wrap" },
  emptyText: { fontSize: 13 },
  statusRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10, marginBottom: 10 },
  voltRow: { flexDirection: "row", gap: 8, paddingTop: 10, borderTopWidth: 1 },
  infoChip: { flex: 1, borderRadius: 10, padding: 10, alignItems: "center", gap: 3 },
  sectionLabel: { fontSize: 12, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 10 },
  quickGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 16 },
  quickBtn: {
    flex: 1,
    minWidth: "47%",
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
  },
  quickIconWrap: {
    width: 34,
    height: 34,
    borderRadius: 9,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: palette.blueLight,
  },
  quickText: { fontWeight: "700", fontSize: 13, flexShrink: 1 },
});
