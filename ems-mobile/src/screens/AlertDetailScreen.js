import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from "react-native";
import { AlertOctagon, AlertTriangle, Calendar, CheckCircle2, Info, Tag } from "lucide-react-native";
import { Badge } from "../components/Badge";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { dataApi } from "../api/endpoints";
import { fmtDate } from "../utils/format";

const SEVERITY_META = {
  CRITICAL: { color: palette.danger, bg: palette.dangerLight, icon: AlertOctagon },
  WARNING:  { color: "#B45309",      bg: palette.solarLight,  icon: AlertTriangle },
  INFO:     { color: palette.blue,   bg: palette.blueLight,   icon: Info },
};

export default function AlertDetailScreen({ route, navigation }) {
  const t = useTheme();
  const { alert, reload } = route.params;
  const meta = SEVERITY_META[alert.severity] || SEVERITY_META.INFO;
  const IconComp = meta.icon;

  async function acknowledge() {
    try {
      await dataApi.acknowledge(alert.id);
      reload && reload();
      navigation.goBack();
    } catch {}
  }

  return (
    <ScrollView
      style={{ backgroundColor: t.bg }}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      {/* Severity header */}
      <View style={[styles.severityHeader, { backgroundColor: meta.bg, borderColor: meta.border || meta.color + "40" }]}>
        <View style={[styles.severityIconWrap, { backgroundColor: meta.color + "22" }]}>
          <IconComp color={meta.color} size={28} strokeWidth={2.2} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[styles.severityLabel, { color: meta.color }]}>{alert.severity}</Text>
          <Text style={[styles.readStatus, { color: meta.color + "CC" }]}>
            {alert.is_read ? "Alerte lue" : "Non lue — action requise"}
          </Text>
        </View>
        {!alert.is_read && <View style={styles.urgentDot} />}
      </View>

      {/* Message */}
      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.cardLabel, { color: t.sub }]}>Message</Text>
        <Text style={[styles.message, { color: t.text }]}>{alert.message}</Text>
      </View>

      {/* Details */}
      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.cardLabel, { color: t.sub }]}>Détails</Text>
        <InfoRow icon={Tag} label="Type" value={alert.alert_type} color={palette.purple} t={t} />
        <InfoRow icon={Calendar} label="Date" value={fmtDate(alert.created_at)} color={palette.blue} t={t} />
        <InfoRow
          icon={CheckCircle2}
          label="Statut"
          value={alert.is_read ? "Lue" : "Non lue"}
          color={alert.is_read ? palette.green : palette.solar}
          t={t}
          isLast
        />
      </View>

      {/* Acknowledge button */}
      {!alert.is_read && (
        <TouchableOpacity
          style={[styles.ackBtn, { backgroundColor: palette.green }]}
          onPress={acknowledge}
          activeOpacity={0.85}
        >
          <CheckCircle2 color="#fff" size={18} strokeWidth={2.4} />
          <Text style={styles.ackBtnText}>Acquitter l'alerte</Text>
        </TouchableOpacity>
      )}

      {alert.is_read && (
        <View style={[styles.alreadyRead, { backgroundColor: palette.greenLight, borderColor: "#86EFAC" }]}>
          <CheckCircle2 color={palette.green} size={16} strokeWidth={2.4} />
          <Text style={{ color: palette.green, fontWeight: "700", fontSize: 13 }}>
            Cette alerte a déjà été acquittée
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

function InfoRow({ icon: Icon, label, value, color, t, isLast }) {
  return (
    <View style={[styles.infoRow, !isLast && { borderBottomWidth: 1, borderBottomColor: t.border }]}>
      <View style={[styles.infoIconWrap, { backgroundColor: color + "15" }]}>
        <Icon color={color} size={14} strokeWidth={2.4} />
      </View>
      <Text style={[styles.infoLabel, { color: t.sub }]}>{label}</Text>
      <Text style={[styles.infoValue, { color: t.text }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, paddingBottom: 32 },

  severityHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    marginBottom: 14,
  },
  severityIconWrap: {
    width: 52,
    height: 52,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  severityLabel: { fontSize: 20, fontWeight: "800" },
  readStatus: { fontSize: 13, marginTop: 2 },
  urgentDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: palette.danger,
  },

  card: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
  },
  cardLabel: { fontSize: 11, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 10 },
  message: { fontSize: 16, fontWeight: "600", lineHeight: 24 },

  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 11,
    gap: 10,
  },
  infoIconWrap: {
    width: 26,
    height: 26,
    borderRadius: 7,
    alignItems: "center",
    justifyContent: "center",
  },
  infoLabel: { flex: 1, fontSize: 13 },
  infoValue: { fontSize: 13, fontWeight: "700" },

  ackBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    padding: 16,
    borderRadius: 14,
    marginTop: 4,
  },
  ackBtnText: { color: "#fff", fontWeight: "800", fontSize: 15 },

  alreadyRead: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginTop: 4,
  },
});
