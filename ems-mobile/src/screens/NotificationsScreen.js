import { useEffect, useState } from "react";
import { ScrollView, View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { AlertOctagon, AlertTriangle, Bell, FileText } from "lucide-react-native";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { useAuthStore } from "../store/auth";

const NOTIFICATION_OPTIONS = [
  {
    key: "critical",
    label: "Alertes critiques",
    description: "Panne, surtension, SoC batterie critique.",
    icon: AlertOctagon,
    color: palette.danger,
  },
  {
    key: "system",
    label: "Alertes système",
    description: "Connexion perdue, capteur hors ligne.",
    icon: AlertTriangle,
    color: palette.solar,
  },
  {
    key: "reports",
    label: "Rapports périodiques",
    description: "Résumé quotidien ou hebdomadaire de consommation.",
    icon: FileText,
    color: palette.blue,
  },
];

const defaultNotifications = { critical: true, system: true, reports: false };

export default function NotificationsScreen() {
  const t = useTheme();
  const { user, updateUser } = useAuthStore();
  const [notifications, setNotifications] = useState(defaultNotifications);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setNotifications({
      ...defaultNotifications,
      ...(user?.preferences?.notifications || {}),
    });
  }, [user]);

  function toggle(key) {
    setNotifications((n) => ({ ...n, [key]: !n[key] }));
  }

  async function save() {
    try {
      await updateUser({
        preferences: { ...(user?.preferences || {}), notifications },
      });
      flash("Préférences enregistrées.");
    } catch {
      flash("Enregistrement impossible.", true);
    }
  }

  function flash(msg, isError = false) {
    if (isError) { setError(msg); setMessage(""); }
    else          { setMessage(msg); setError(""); }
    setTimeout(() => { setMessage(""); setError(""); }, 3000);
  }

  return (
    <ScrollView
      style={{ backgroundColor: t.bg }}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      {/* Icon block */}
      <View style={[styles.iconBlock, { backgroundColor: palette.blue + "14" }]}>
        <Bell color={palette.blue} size={38} strokeWidth={1.8} />
      </View>

      {message ? <Toast text={message} color={palette.green} /> : null}
      {error   ? <Toast text={error}   color={palette.danger} /> : null}

      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.cardTitle, { color: t.text }]}>Notifications push</Text>
        <Text style={[styles.cardSub, { color: t.sub }]}>
          Choisissez les types d'alertes à recevoir sur votre appareil.
        </Text>

        {NOTIFICATION_OPTIONS.map(({ key, label, description, icon: Icon, color }) => {
          const active = notifications[key];
          return (
            <TouchableOpacity
              key={key}
              style={[
                styles.toggleRow,
                { borderColor: active ? color + "40" : t.border, backgroundColor: active ? color + "08" : "transparent" },
              ]}
              onPress={() => toggle(key)}
              activeOpacity={0.75}
            >
              <View style={[styles.toggleIcon, { backgroundColor: color + "18" }]}>
                <Icon color={color} size={17} strokeWidth={2.4} />
              </View>
              <View style={styles.toggleText}>
                <Text style={[styles.toggleLabel, { color: t.text }]}>{label}</Text>
                <Text style={[styles.toggleDesc, { color: t.sub }]}>{description}</Text>
              </View>
              <View style={[styles.pill, { backgroundColor: active ? color : t.border }]}>
                <View style={[styles.knob, { marginLeft: active ? 14 : 2 }]} />
              </View>
            </TouchableOpacity>
          );
        })}

        <TouchableOpacity
          style={[styles.saveBtn, { backgroundColor: palette.blue }]}
          onPress={save}
          activeOpacity={0.85}
        >
          <Bell color="#fff" size={16} strokeWidth={2.4} />
          <Text style={{ color: "#fff", fontWeight: "700", fontSize: 14 }}>
            Enregistrer
          </Text>
        </TouchableOpacity>
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

function Toast({ text, color }) {
  return (
    <View style={[styles.toast, { backgroundColor: color }]}>
      <Text style={styles.toastText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { paddingBottom: 24 },
  iconBlock: {
    width: 80, height: 80, borderRadius: 24,
    alignItems: "center", justifyContent: "center",
    alignSelf: "center", marginTop: 24, marginBottom: 8,
  },
  toast: { margin: 14, marginBottom: 0, padding: 12, borderRadius: 10 },
  toastText: { color: "#fff", fontWeight: "700", textAlign: "center" },

  card: { marginHorizontal: 14, marginTop: 14, borderRadius: 14, borderWidth: 1, padding: 16 },
  cardTitle: { fontSize: 15, fontWeight: "800", marginBottom: 4 },
  cardSub: { fontSize: 13, lineHeight: 18, marginBottom: 14 },

  toggleRow: {
    flexDirection: "row", alignItems: "center", gap: 12,
    borderWidth: 1.5, borderRadius: 12, padding: 14, marginBottom: 10,
  },
  toggleIcon: { width: 36, height: 36, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  toggleText: { flex: 1 },
  toggleLabel: { fontWeight: "700", fontSize: 14, marginBottom: 2 },
  toggleDesc: { fontSize: 12, lineHeight: 17 },
  pill: { width: 36, height: 22, borderRadius: 11, justifyContent: "center" },
  knob: { width: 18, height: 18, borderRadius: 9, backgroundColor: "#fff" },

  saveBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, padding: 13, borderRadius: 10, marginTop: 6,
  },
});
