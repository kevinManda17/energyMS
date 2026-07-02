import { useEffect, useState } from "react";
import { ScrollView, View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";
import { CheckCircle2, LogOut, Mail, Phone, User, Wifi } from "lucide-react-native";
import { Badge } from "../components/Badge";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { useAuthStore } from "../store/auth";
import { storage } from "../storage";
import { API_PRESETS } from "../api/config";

export default function ProfileScreen() {
  const t = useTheme();
  const { user, updateUser, logout } = useAuthStore();
  const [profile, setProfile] = useState({ first_name: "", last_name: "", email: "", phone: "" });
  const [apiMode, setApiMode] = useState("cloud");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setProfile({
      first_name: user?.first_name || "",
      last_name:  user?.last_name  || "",
      email:      user?.email      || "",
      phone:      user?.phone      || "",
    });
    storage.getApiMode().then(setApiMode).catch(() => {});
  }, [user]);

  function flash(msg, isError = false) {
    if (isError) setError(msg); else setMessage(msg);
    setTimeout(() => { setMessage(""); setError(""); }, 3000);
  }

  async function saveProfile() {
    try {
      await updateUser({ ...profile });
      flash("Profil enregistré.");
    } catch {
      flash("Enregistrement impossible.", true);
    }
  }

  return (
    <ScrollView
      style={{ backgroundColor: t.bg }}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      {/* Hero */}
      <View style={[styles.hero, { backgroundColor: palette.blue }]}>
        <View style={styles.avatarCircle}>
          <Text style={styles.avatarText}>
            {(user?.first_name?.[0] || user?.email?.[0] || "U").toUpperCase()}
          </Text>
        </View>
        <Text style={styles.heroName}>
          {user?.first_name
            ? `${user.first_name} ${user.last_name || ""}`.trim()
            : user?.email || "Utilisateur"}
        </Text>
        <Text style={styles.heroEmail}>{user?.email || ""}</Text>
        <View style={[styles.heroBadge, { backgroundColor: "rgba(255,255,255,0.18)" }]}>
          <Text style={{ color: "#fff", fontSize: 11, fontWeight: "700" }}>
            {user?.phone_verified ? "Téléphone vérifié" : "Non vérifié"}
          </Text>
        </View>
      </View>

      {message ? <Toast text={message} color={palette.green} /> : null}
      {error   ? <Toast text={error}   color={palette.danger} /> : null}

      {/* Informations */}
      <Card t={t} title="Informations personnelles">
        <Field
          label="Prénom"
          value={profile.first_name}
          onChangeText={(v) => setProfile((p) => ({ ...p, first_name: v }))}
          icon={User}
          t={t}
        />
        <Field
          label="Nom"
          value={profile.last_name}
          onChangeText={(v) => setProfile((p) => ({ ...p, last_name: v }))}
          icon={User}
          t={t}
        />
        <Field
          label="Adresse e-mail"
          value={profile.email}
          onChangeText={(v) => setProfile((p) => ({ ...p, email: v }))}
          icon={Mail}
          keyboardType="email-address"
          autoCapitalize="none"
          t={t}
        />
        <Field
          label="Téléphone"
          value={profile.phone}
          onChangeText={(v) => setProfile((p) => ({ ...p, phone: v }))}
          icon={Phone}
          keyboardType="phone-pad"
          t={t}
        />
        <View style={styles.badgeRow}>
          <Badge value={user?.phone_verified ? "VALID" : "WARNING"} />
          <Text style={{ color: t.sub, fontSize: 12 }}>
            {user?.phone_verified ? "Téléphone vérifié" : "Téléphone non vérifié"}
          </Text>
        </View>
        <ActionBtn label="Enregistrer le profil" onPress={saveProfile} />
      </Card>

      {/* Connexions */}
      <Card t={t} title="Connexions">
        <InfoRow label="Mode de connexion" value={
          apiMode === "cloud" ? "Cloud" : apiMode === "edge" ? "Edge" : "URL locale"
        } t={t} />
        <InfoRow
          label="Serveur"
          value={API_PRESETS?.[apiMode] || "Personnalisé"}
          t={t}
        />
        <InfoRow
          label="Statut téléphone"
          value={user?.phone_verified ? "Vérifié" : "Non vérifié"}
          t={t}
        />
        <View style={styles.wifiRow}>
          <Wifi color={palette.green} size={14} strokeWidth={2.2} />
          <Text style={{ color: palette.green, fontSize: 12, fontWeight: "700" }}>
            Session active
          </Text>
          <Text style={{ color: t.sub, fontSize: 12, marginLeft: "auto" }}>
            {user?.username || user?.email || ""}
          </Text>
        </View>
      </Card>

      {/* Déconnexion */}
      <TouchableOpacity
        style={[styles.logoutBtn, { borderColor: palette.danger }]}
        onPress={logout}
        activeOpacity={0.7}
      >
        <LogOut color={palette.danger} size={18} strokeWidth={2.2} />
        <Text style={{ color: palette.danger, fontWeight: "800", fontSize: 15 }}>
          Déconnexion
        </Text>
      </TouchableOpacity>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

/* ── Sub-components ── */

function Card({ t, title, children }) {
  return (
    <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
      <Text style={[styles.cardTitle, { color: t.text }]}>{title}</Text>
      {children}
    </View>
  );
}

function Field({ label, icon: Icon, t, ...props }) {
  return (
    <View style={{ marginTop: 12 }}>
      <Text style={[styles.fieldLabel, { color: t.sub }]}>{label}</Text>
      <View style={[styles.inputWrap, { borderColor: t.border }]}>
        {Icon && <Icon color={t.sub} size={15} strokeWidth={2.2} style={{ marginRight: 8 }} />}
        <TextInput
          style={[styles.input, { color: t.text }]}
          placeholderTextColor={t.sub}
          autoCapitalize="none"
          selectionColor={palette.blue}
          {...props}
        />
      </View>
    </View>
  );
}

function InfoRow({ label, value, t }) {
  return (
    <View style={[styles.infoRow, { borderBottomColor: t.border }]}>
      <Text style={{ color: t.sub, fontSize: 13 }}>{label}</Text>
      <Text style={{ color: t.text, fontSize: 13, fontWeight: "600" }}>{value}</Text>
    </View>
  );
}

function ActionBtn({ label, onPress, color = palette.blue }) {
  return (
    <TouchableOpacity
      style={[styles.actionBtn, { backgroundColor: color }]}
      onPress={onPress}
      activeOpacity={0.8}
    >
      <Text style={{ color: "#fff", fontWeight: "700", fontSize: 14 }}>{label}</Text>
    </TouchableOpacity>
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

  hero: { alignItems: "center", paddingTop: 28, paddingBottom: 26, gap: 4 },
  avatarCircle: {
    width: 64, height: 64, borderRadius: 32,
    backgroundColor: "rgba(255,255,255,0.25)",
    alignItems: "center", justifyContent: "center", marginBottom: 8,
  },
  avatarText: { color: "#fff", fontSize: 26, fontWeight: "800" },
  heroName: { color: "#fff", fontSize: 18, fontWeight: "800" },
  heroEmail: { color: "rgba(255,255,255,0.75)", fontSize: 13 },
  heroBadge: { marginTop: 6, paddingHorizontal: 12, paddingVertical: 4, borderRadius: 999 },

  toast: { margin: 14, marginBottom: 0, padding: 12, borderRadius: 10 },
  toastText: { color: "#fff", fontWeight: "700", textAlign: "center" },

  card: {
    marginHorizontal: 14, marginTop: 14,
    borderRadius: 14, borderWidth: 1, padding: 16,
  },
  cardTitle: { fontSize: 15, fontWeight: "800", marginBottom: 4 },

  fieldLabel: { fontSize: 12, marginBottom: 4 },
  inputWrap: {
    borderWidth: 1, borderRadius: 10, minHeight: 46,
    paddingHorizontal: 12, flexDirection: "row", alignItems: "center",
  },
  input: { flex: 1, paddingVertical: 10, fontSize: 14, backgroundColor: "transparent" },

  infoRow: {
    flexDirection: "row", justifyContent: "space-between",
    paddingVertical: 9, borderBottomWidth: 0.5,
  },

  wifiRow: {
    flexDirection: "row", alignItems: "center", gap: 8,
    marginTop: 10, padding: 10,
    backgroundColor: "rgba(22,163,74,0.08)", borderRadius: 10,
  },

  badgeRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 12 },
  actionBtn: { padding: 13, borderRadius: 10, alignItems: "center", marginTop: 14 },

  logoutBtn: {
    marginHorizontal: 14, marginTop: 20,
    borderWidth: 1.5, borderRadius: 12, padding: 15,
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 10,
  },
});
