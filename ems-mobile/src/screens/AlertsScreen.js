import { useEffect, useState, useCallback } from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from "react-native";
import { AlertOctagon, AlertTriangle, Bell, Info } from "lucide-react-native";
import { Badge } from "../components/Badge";
import { Screen, PageTitle } from "../components/Screen";
import { useTheme } from "../hooks/useTheme";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { alertsApi } from "../api/endpoints";
import { fmtDate } from "../utils/format";
import { palette } from "../theme/colors";

const SEVERITIES = ["all", "CRITICAL", "WARNING", "INFO"];
const STATUSES = [["all", "Toutes"], ["unread", "Non lues"], ["read", "Lues"]];

const SEVERITY_META = {
  CRITICAL: { color: palette.danger, bg: palette.dangerLight, icon: AlertOctagon, border: "#FCA5A5" },
  WARNING:  { color: "#B45309",      bg: palette.solarLight,  icon: AlertTriangle, border: "#FCD34D" },
  INFO:     { color: palette.blue,   bg: palette.blueLight,   icon: Info,         border: "#93C5FD" },
};

export default function AlertsScreen({ navigation }) {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [alerts, setAlerts] = useState([]);
  const [severity, setSeverity] = useState("all");
  const [status, setStatus] = useState("all");

  const load = useCallback(() => {
    const params = { page_size: 80 };
    if (houseId) params.house = houseId;
    if (severity !== "all") params.severity = severity;
    if (status !== "all") params.is_read = status === "read";
    alertsApi
      .list(params)
      .then((r) => setAlerts(r.data?.results || r.data || []))
      .catch(() => {});
  }, [houseId, severity, status]);

  useEffect(() => load(), [load]);

  const unreadCount = alerts.filter((a) => !a.is_read).length;

  return (
    <Screen>
      <View style={styles.headerRow}>
        <View>
          <PageTitle
            title="Alertes"
            subtitle={activeHouse?.name || "Tous les micro-réseaux"}
          />
        </View>
        {unreadCount > 0 && (
          <View style={styles.unreadBadge}>
            <Text style={styles.unreadText}>{unreadCount} non lue{unreadCount > 1 ? "s" : ""}</Text>
          </View>
        )}
      </View>

      {/* Severity filters */}
      <View style={styles.filterRow}>
        {SEVERITIES.map((item) => {
          const meta = SEVERITY_META[item];
          const active = severity === item;
          return (
            <TouchableOpacity
              key={item}
              onPress={() => setSeverity(item)}
              style={[
                styles.chip,
                {
                  borderColor: active ? (meta?.color || palette.blue) : t.border,
                  backgroundColor: active ? (meta?.bg || palette.blueLight) : "transparent",
                },
              ]}
            >
              {meta?.icon ? (
                <meta.icon
                  color={active ? meta.color : t.sub}
                  size={12}
                  strokeWidth={2.4}
                />
              ) : (
                <Bell color={active ? palette.blue : t.sub} size={12} strokeWidth={2.4} />
              )}
              <Text style={{ color: active ? (meta?.color || palette.blue) : t.sub, fontSize: 12, fontWeight: "700" }}>
                {item === "all" ? "Toutes" : item}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Status filters */}
      <View style={[styles.filterRow, { marginBottom: 10 }]}>
        {STATUSES.map(([id, label]) => (
          <TouchableOpacity
            key={id}
            onPress={() => setStatus(id)}
            style={[
              styles.chip,
              {
                borderColor: status === id ? palette.blue : t.border,
                backgroundColor: status === id ? palette.blueLight : "transparent",
              },
            ]}
          >
            <Text style={{ color: status === id ? palette.blue : t.sub, fontSize: 12, fontWeight: "700" }}>
              {label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <FlatList
        data={alerts}
        keyExtractor={(i) => String(i.id)}
        renderItem={({ item }) => {
          const meta = SEVERITY_META[item.severity] || SEVERITY_META.INFO;
          const IconComp = meta.icon;
          return (
            <TouchableOpacity
              onPress={() => navigation.navigate("AlertDetail", { alert: item, reload: load })}
              activeOpacity={0.75}
            >
              <View
                style={[
                  styles.alertCard,
                  {
                    backgroundColor: t.card,
                    borderColor: t.border,
                    borderLeftColor: meta.color,
                  },
                ]}
              >
                <View style={[styles.alertIconWrap, { backgroundColor: meta.bg }]}>
                  <IconComp color={meta.color} size={18} strokeWidth={2.4} />
                </View>
                <View style={styles.alertBody}>
                  <View style={styles.alertTop}>
                    <Text style={[styles.alertMsg, { color: t.text }]} numberOfLines={2}>
                      {item.message}
                    </Text>
                    {!item.is_read && <View style={styles.unreadDot} />}
                  </View>
                  <View style={styles.alertMeta}>
                    <Text style={[styles.alertType, { color: t.sub }]}>{item.alert_type}</Text>
                    <Text style={[styles.alertDate, { color: t.sub }]}>{fmtDate(item.created_at)}</Text>
                  </View>
                </View>
              </View>
            </TouchableOpacity>
          );
        }}
        ListEmptyComponent={
          <View style={styles.emptyWrap}>
            <Bell color={t.sub} size={40} strokeWidth={1.5} />
            <Text style={[styles.emptyText, { color: t.sub }]}>Aucune alerte.</Text>
          </View>
        }
        showsVerticalScrollIndicator={false}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  unreadBadge: {
    backgroundColor: palette.dangerLight,
    borderWidth: 1,
    borderColor: "#FCA5A5",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    marginTop: 8,
  },
  unreadText: { color: palette.danger, fontSize: 11, fontWeight: "700" },
  filterRow: { flexDirection: "row", flexWrap: "wrap", gap: 7, marginBottom: 6 },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  alertCard: {
    flexDirection: "row",
    borderWidth: 1,
    borderLeftWidth: 4,
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    gap: 12,
    alignItems: "flex-start",
  },
  alertIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  alertBody: { flex: 1 },
  alertTop: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginBottom: 6 },
  alertMsg: { flex: 1, fontWeight: "700", fontSize: 14, lineHeight: 20 },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: palette.blue,
    marginTop: 4,
  },
  alertMeta: { flexDirection: "row", justifyContent: "space-between", gap: 8 },
  alertType: { fontSize: 12, fontWeight: "600" },
  alertDate: { fontSize: 11 },
  emptyWrap: { alignItems: "center", marginTop: 60, gap: 12 },
  emptyText: { fontSize: 15 },
});
