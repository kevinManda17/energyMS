import { useEffect, useState } from "react";
import { ScrollView, View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";
import {
  Bell,
  Eye,
  EyeOff,
  Lock,
  LogOut,
  Palette,
  Shield,
  User,
  Wifi,
} from "lucide-react-native";
import { Badge } from "../components/Badge";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { storage } from "../storage";
import { API_PRESETS } from "../api/config";
import { authApi } from "../api/endpoints";
import { useAuthStore } from "../store/auth";

const MODES = [
  { id: "cloud", label: "Cloud" },
  { id: "edge", label: "Edge" },
  { id: "local", label: "URL locale" },
];

const defaultPreferences = {
  theme: "system",
  language: "fr",
  units: "metric",
  notifications: { critical: true, system: true, reports: false },
};

export default function SettingsScreen() {
  const t = useTheme();
  const { user, updateUser, logout } = useAuthStore();
  const [mode, setMode] = useState("cloud");
  const [custom, setCustom] = useState("");
  const [profile, setProfile] = useState({});
  const [preferences, setPreferences] = useState(defaultPreferences);
  const [passwords, setPasswords] = useState({
    current_password: "",
    new_password: "",
    password_confirm: "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    storage.getApiMode().then(setMode);
    storage.getCustomUrl().then((u) => setCustom(u || ""));
  }, []);

  useEffect(() => {
    setProfile({
      first_name: user?.first_name || "",
      last_name: user?.last_name || "",
      email: user?.email || "",
      phone: user?.phone || "",
    });
    setPreferences({ ...defaultPreferences, ...(user?.preferences || {}) });
  }, [user]);

  async function selectMode(id) {
    setMode(id);
    await storage.setApiMode(id);
  }

  async function saveCustom() {
    await storage.setCustomUrl(custom);
    flash("URL API enregistree.");
  }

  async function saveProfile() {
    setMessage("");
    setError("");
    try {
      await updateUser({ ...profile, preferences });
      flash("Profil enregistre.");
    } catch {
      setError("Enregistrement impossible.");
    }
  }

  async function savePreferences(next = preferences) {
    setPreferences(next);
    try {
      await updateUser({ preferences: next });
      flash("Preferences enregistrees.");
    } catch {
      setError("Enregistrement impossible.");
    }
  }

  async function changePassword() {
    setMessage("");
    setError("");
    try {
      await authApi.changePassword(passwords);
      setPasswords({ current_password: "", new_password: "", password_confirm: "" });
      flash("Mot de passe modifie.");
    } catch {
      setError("Mot de passe non modifie.");
    }
  }

  function setNotification(key, value) {
    setPreferences({
      ...preferences,
      notifications: { ...preferences.notifications, [key]: value },
    });
  }

  function flash(msg) {
    setMessage(msg);
    setTimeout(() => setMessage(""), 3000);
  }

  return (
    <ScrollView
      style={{ backgroundColor: t.bg }}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      {/* Header */}
      <View style={[styles.profileHeader, { backgroundColor: palette.blue }]}>
        <View style={styles.avatarCircle}>
          <Text style={styles.avatarText}>
            {(user?.first_name?.[0] || user?.email?.[0] || "U").toUpperCase()}
          </Text>
        </View>
        <Text style={styles.profileName}>
          {user?.first_name ? `${user.first_name} ${user.last_name || ""}`.trim() : user?.email || "Utilisateur"}
        </Text>
        <Text style={styles.profileEmail}>{user?.email || ""}</Text>
      </View>

      {message ? (
        <View style={[styles.toast, { backgroundColor: palette.green }]}>
          <Text style={styles.toastText}>{message}</Text>
        </View>
      ) : null}
      {error ? (
        <View style={[styles.toast, { backgroundColor: palette.danger }]}>
          <Text style={styles.toastText}>{error}</Text>
        </View>
      ) : null}

      <Section icon={User} title="Profil" color={palette.blue} t={t}>
        <Input label="Prenom" value={profile.first_name} onChangeText={(v) => setProfile({ ...profile, first_name: v })} t={t} />
        <Input label="Nom" value={profile.last_name} onChangeText={(v) => setProfile({ ...profile, last_name: v })} t={t} />
        <Input label="E-mail" value={profile.email} onChangeText={(v) => setProfile({ ...profile, email: v })} t={t} />
        <Input label="Telephone" value={profile.phone} onChangeText={(v) => setProfile({ ...profile, phone: v })} t={t} />
        <View style={styles.badgeRow}>
          <Badge value={user?.phone_verified ? "VALID" : "WARNING"} />
          <Text style={{ color: t.sub, fontSize: 12 }}>
            {user?.phone_verified ? "Telephone verifie" : "Telephone non verifie"}
          </Text>
        </View>
        <Button label="Enregistrer le profil" onPress={saveProfile} />
      </Section>

      <Section icon={Lock} title="Securite" color="#7C3AED" t={t}>
        <Input label="Mot de passe actuel" value={passwords.current_password} onChangeText={(v) => setPasswords({ ...passwords, current_password: v })} t={t} secureTextEntry />
        <Input label="Nouveau mot de passe" value={passwords.new_password} onChangeText={(v) => setPasswords({ ...passwords, new_password: v })} t={t} secureTextEntry />
        <Input label="Confirmation" value={passwords.password_confirm} onChangeText={(v) => setPasswords({ ...passwords, password_confirm: v })} t={t} secureTextEntry />
        <Button label="Modifier le mot de passe" onPress={changePassword} color="#7C3AED" />
      </Section>

      <Section icon={Palette} title="Affichage" color={palette.solar} t={t}>
        <Text style={[styles.fieldLabel, { color: t.sub }]}>Theme</Text>
        <Segmented
          t={t}
          value={preferences.theme}
          options={[["light", "Clair"], ["dark", "Sombre"], ["system", "Systeme"]]}
          onChange={(theme) => savePreferences({ ...preferences, theme })}
        />
        <InfoRow label="Langue" value="Francais" t={t} />
        <InfoRow label="Unites" value="kW · kWh · V · A · °C" t={t} />
      </Section>

      <Section icon={Bell} title="Notifications" color={palette.green} t={t}>
        <Toggle label="Alertes critiques" value={preferences.notifications?.critical} onChange={(v) => setNotification("critical", v)} t={t} />
        <Toggle label="Alertes systeme" value={preferences.notifications?.system} onChange={(v) => setNotification("system", v)} t={t} />
        <Toggle label="Rapports" value={preferences.notifications?.reports} onChange={(v) => setNotification("reports", v)} t={t} />
        <Button label="Enregistrer les notifications" onPress={() => savePreferences(preferences)} color={palette.green} />
      </Section>

      <Section icon={Wifi} title="API mobile" color={palette.navy} t={t}>
        <View style={styles.modeGroup}>
          {MODES.map((item) => (
            <TouchableOpacity
              key={item.id}
              style={[styles.modeChip, { borderColor: mode === item.id ? palette.blue : t.border, backgroundColor: mode === item.id ? palette.blue + "14" : "transparent" }]}
              onPress={() => selectMode(item.id)}
            >
              <Text style={{ color: mode === item.id ? palette.blue : t.text, fontWeight: "700", fontSize: 13 }}>{item.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <Text style={[styles.hint, { color: t.sub }]}>Cloud: {API_PRESETS.cloud}</Text>
        <Text style={[styles.hint, { color: t.sub }]}>Edge: {API_PRESETS.edge}</Text>
        {mode === "local" && (
          <>
            <Input label="URL personnalisee" value={custom} onChangeText={setCustom} placeholder="http://172.20.10.2:8000/api" t={t} />
            <Button label="Enregistrer l'URL" onPress={saveCustom} />
          </>
        )}
      </Section>

      <Section icon={Shield} title="Confidentialite" color={palette.slate} t={t}>
        <InfoRow label="Export" value="Via l'ecran Rapports" t={t} />
        <InfoRow label="Suppression compte" value="Non disponible" t={t} />
      </Section>

      <TouchableOpacity style={[styles.logoutBtn, { borderColor: palette.danger }]} onPress={logout} activeOpacity={0.7}>
        <LogOut color={palette.danger} size={18} strokeWidth={2.2} />
        <Text style={{ color: palette.danger, fontWeight: "800", fontSize: 15 }}>Deconnexion</Text>
      </TouchableOpacity>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

/* Sub-components */

function Section({ icon: Icon, title, color, children, t }) {
  return (
    <View style={[styles.section, { backgroundColor: t.card, borderColor: t.border }]}>
      <View style={styles.sectionHead}>
        <View style={[styles.sectionIcon, { backgroundColor: color + "18" }]}>
          <Icon color={color} size={16} strokeWidth={2.4} />
        </View>
        <Text style={[styles.sectionTitle, { color: t.text }]}>{title}</Text>
      </View>
      <View style={styles.sectionBody}>{children}</View>
    </View>
  );
}

function InfoRow({ label, value, t }) {
  return (
    <View style={styles.infoRow}>
      <Text style={{ color: t.sub, fontSize: 13 }}>{label}</Text>
      <Text style={{ color: t.text, fontSize: 13, fontWeight: "600" }}>{value}</Text>
    </View>
  );
}

function Input({ label, t, ...props }) {
  const [hidden, setHidden] = useState(!!props.secureTextEntry);
  const isPassword = !!props.secureTextEntry;
  return (
    <View style={{ marginTop: 12 }}>
      <Text style={[styles.fieldLabel, { color: t.sub }]}>{label}</Text>
      <View style={[styles.inputWrap, { borderColor: t.border }]}>
        <TextInput
          key={isPassword ? (hidden ? "password-hidden" : "password-visible") : "plain"}
          style={[styles.input, { color: t.text }]}
          placeholderTextColor={t.sub}
          autoCapitalize="none"
          underlineColorAndroid="transparent"
          selectionColor={palette.blue}
          {...props}
          secureTextEntry={isPassword ? hidden : false}
          textContentType={isPassword ? "password" : "none"}
        />
        {isPassword ? (
          <TouchableOpacity
            accessibilityLabel={hidden ? "Afficher le mot de passe" : "Masquer le mot de passe"}
            style={styles.eyeButton}
            onPress={() => setHidden((current) => !current)}
          >
            {hidden ? (
              <Eye color={palette.blue} size={18} strokeWidth={2.2} />
            ) : (
              <EyeOff color={palette.blue} size={18} strokeWidth={2.2} />
            )}
          </TouchableOpacity>
        ) : null}
      </View>
    </View>
  );
}

function Button({ label, onPress, color = palette.blue }) {
  return (
    <TouchableOpacity style={[styles.saveBtn, { backgroundColor: color }]} onPress={onPress} activeOpacity={0.8}>
      <Text style={{ color: "#fff", fontWeight: "700", fontSize: 14 }}>{label}</Text>
    </TouchableOpacity>
  );
}

function Segmented({ value, options, onChange, t }) {
  return (
    <View style={styles.segmented}>
      {options.map(([id, label]) => (
        <TouchableOpacity
          key={id}
          onPress={() => onChange(id)}
          style={[
            styles.segment,
            {
              borderColor: value === id ? palette.blue : t.border,
              backgroundColor: value === id ? palette.blue : "transparent",
            },
          ]}
        >
          <Text style={{ color: value === id ? "#fff" : t.text, fontWeight: "700", fontSize: 13 }}>{label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

function Toggle({ label, value, onChange, t }) {
  return (
    <TouchableOpacity style={[styles.toggle, { borderColor: t.border }]} onPress={() => onChange(!value)}>
      <Text style={{ color: t.text, fontSize: 14 }}>{label}</Text>
      <View style={[styles.togglePill, { backgroundColor: value ? palette.green : t.border }]}>
        <View style={[styles.toggleKnob, { marginLeft: value ? 14 : 2 }]} />
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { paddingBottom: 24 },

  profileHeader: {
    paddingTop: 28,
    paddingBottom: 28,
    alignItems: "center",
    gap: 6,
  },
  avatarCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "rgba(255,255,255,0.25)",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 6,
  },
  avatarText: { color: "#fff", fontSize: 26, fontWeight: "800" },
  profileName: { color: "#fff", fontSize: 18, fontWeight: "800" },
  profileEmail: { color: "rgba(255,255,255,0.8)", fontSize: 13 },

  toast: { margin: 14, marginBottom: 0, padding: 12, borderRadius: 8 },
  toastText: { color: "#fff", fontWeight: "700", textAlign: "center" },

  section: {
    marginHorizontal: 14,
    marginTop: 14,
    borderRadius: 12,
    borderWidth: 1,
    overflow: "hidden",
  },
  sectionHead: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(0,0,0,0.06)",
  },
  sectionIcon: {
    width: 28,
    height: 28,
    borderRadius: 7,
    alignItems: "center",
    justifyContent: "center",
  },
  sectionTitle: { fontSize: 15, fontWeight: "800" },
  sectionBody: { padding: 16 },

  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
    borderBottomWidth: 0.5,
    borderBottomColor: "rgba(0,0,0,0.05)",
  },
  fieldLabel: { fontSize: 12, marginBottom: 4 },
  inputWrap: {
    borderWidth: 1,
    borderRadius: 8,
    minHeight: 46,
    paddingHorizontal: 12,
    flexDirection: "row",
    alignItems: "center",
  },
  input: { flex: 1, paddingVertical: 10, backgroundColor: "transparent", fontSize: 14 },
  eyeButton: { width: 34, height: 34, alignItems: "center", justifyContent: "center" },
  saveBtn: { padding: 13, borderRadius: 8, alignItems: "center", marginTop: 14 },

  modeGroup: { flexDirection: "row", gap: 8, marginBottom: 10, flexWrap: "wrap" },
  modeChip: { borderWidth: 1.5, borderRadius: 8, paddingHorizontal: 14, paddingVertical: 9 },
  hint: { fontSize: 11, marginTop: 4 },

  badgeRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 12 },

  segmented: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 6, marginBottom: 4 },
  segment: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 14, paddingVertical: 9 },

  toggle: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginTop: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  togglePill: {
    width: 36,
    height: 22,
    borderRadius: 11,
    justifyContent: "center",
  },
  toggleKnob: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: "#fff",
  },

  logoutBtn: {
    marginHorizontal: 14,
    marginTop: 20,
    borderWidth: 1.5,
    borderRadius: 12,
    padding: 15,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
});
