import { useEffect, useState } from "react";
import { ScrollView, View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";
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
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "", password_confirm: "" });
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
    setMessage("URL API enregistree.");
  }

  async function saveProfile() {
    setMessage("");
    setError("");
    try {
      await updateUser({ ...profile, preferences });
      setMessage("Profil enregistre.");
    } catch {
      setError("Enregistrement impossible.");
    }
  }

  async function savePreferences(next = preferences) {
    setPreferences(next);
    try {
      await updateUser({ preferences: next });
      setMessage("Preferences enregistrees.");
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
      setMessage("Mot de passe modifie.");
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

  return (
    <ScrollView style={{ backgroundColor: t.bg }} contentContainerStyle={{ padding: 16 }}>
      <Text style={[styles.h1, { color: t.text }]}>Parametres</Text>

      <Section title="Profil" t={t}>
        <Input label="Prenom" value={profile.first_name} onChangeText={(v) => setProfile({ ...profile, first_name: v })} t={t} />
        <Input label="Nom" value={profile.last_name} onChangeText={(v) => setProfile({ ...profile, last_name: v })} t={t} />
        <Input label="E-mail" value={profile.email} onChangeText={(v) => setProfile({ ...profile, email: v })} t={t} />
        <Input label="Telephone" value={profile.phone} onChangeText={(v) => setProfile({ ...profile, phone: v })} t={t} />
        <View style={styles.badges}>
          <Badge value={user?.phone_verified ? "VALID" : "WARNING"} />
          <Text style={{ color: t.sub }}>{user?.phone_verified ? "Telephone verifie" : "Telephone non verifie"}</Text>
        </View>
        <Button label="Enregistrer le profil" onPress={saveProfile} />
      </Section>

      <Section title="Securite" t={t}>
        <Input label="Mot de passe actuel" value={passwords.current_password} onChangeText={(v) => setPasswords({ ...passwords, current_password: v })} t={t} secureTextEntry />
        <Input label="Nouveau mot de passe" value={passwords.new_password} onChangeText={(v) => setPasswords({ ...passwords, new_password: v })} t={t} secureTextEntry />
        <Input label="Confirmation" value={passwords.password_confirm} onChangeText={(v) => setPasswords({ ...passwords, password_confirm: v })} t={t} secureTextEntry />
        <Button label="Modifier le mot de passe" onPress={changePassword} />
      </Section>

      <Section title="Affichage" t={t}>
        <Segmented
          t={t}
          value={preferences.theme}
          options={[["light", "Clair"], ["dark", "Sombre"], ["system", "Systeme"]]}
          onChange={(theme) => savePreferences({ ...preferences, theme })}
        />
        <Text style={{ color: t.sub }}>Langue: francais</Text>
        <Text style={{ color: t.sub }}>Unites: kW, kWh, V, A, C</Text>
      </Section>

      <Section title="Notifications" t={t}>
        <Toggle label="Alertes critiques" value={preferences.notifications?.critical} onChange={(v) => setNotification("critical", v)} t={t} />
        <Toggle label="Alertes systeme" value={preferences.notifications?.system} onChange={(v) => setNotification("system", v)} t={t} />
        <Toggle label="Rapports" value={preferences.notifications?.reports} onChange={(v) => setNotification("reports", v)} t={t} />
        <Button label="Enregistrer les notifications" onPress={() => savePreferences(preferences)} />
      </Section>

      <Section title="API mobile" t={t}>
        {MODES.map((item) => (
          <TouchableOpacity key={item.id} style={[styles.modeRow, { borderColor: mode === item.id ? palette.blue : t.border }]} onPress={() => selectMode(item.id)}>
            <Text style={{ color: t.text, fontWeight: "700" }}>{item.label}</Text>
            {mode === item.id ? <Text style={{ color: palette.blue, fontWeight: "800" }}>Actif</Text> : null}
          </TouchableOpacity>
        ))}
        <Text style={[styles.hint, { color: t.sub }]}>Cloud: {API_PRESETS.cloud}</Text>
        <Text style={[styles.hint, { color: t.sub }]}>Edge: {API_PRESETS.edge}</Text>
        {mode === "local" && (
          <>
            <Input label="URL personnalisee" value={custom} onChangeText={setCustom} placeholder="http://172.20.10.2:8000/api" t={t} />
            <Button label="Enregistrer l'URL" onPress={saveCustom} />
          </>
        )}
      </Section>

      <Section title="Confidentialite" t={t}>
        <Text style={{ color: t.sub }}>Export des donnees disponible depuis Rapports.</Text>
        <Text style={{ color: t.sub }}>Suppression de compte non activee.</Text>
      </Section>

      {message ? <Text style={styles.message}>{message}</Text> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TouchableOpacity style={styles.logout} onPress={logout}>
        <Text style={{ color: palette.danger, fontWeight: "800" }}>Deconnexion</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

function Section({ title, children, t }) {
  return (
    <View style={[styles.sectionBox, { borderColor: t.border, backgroundColor: t.card }]}>
      <Text style={[styles.section, { color: t.text }]}>{title}</Text>
      {children}
    </View>
  );
}

function Input({ label, t, ...props }) {
  return (
    <View style={{ marginTop: 10 }}>
      <Text style={{ color: t.sub, fontSize: 12, marginBottom: 5 }}>{label}</Text>
      <TextInput style={[styles.input, { color: t.text, borderColor: t.border }]} placeholderTextColor={t.sub} autoCapitalize="none" {...props} />
    </View>
  );
}

function Button({ label, onPress }) {
  return (
    <TouchableOpacity style={styles.saveBtn} onPress={onPress}>
      <Text style={{ color: "#fff", fontWeight: "700" }}>{label}</Text>
    </TouchableOpacity>
  );
}

function Segmented({ value, options, onChange, t }) {
  return (
    <View style={styles.segmented}>
      {options.map(([id, label]) => (
        <TouchableOpacity key={id} onPress={() => onChange(id)} style={[styles.segment, { borderColor: value === id ? palette.blue : t.border, backgroundColor: value === id ? palette.blue : "transparent" }]}>
          <Text style={{ color: value === id ? "#fff" : t.text, fontWeight: "700" }}>{label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

function Toggle({ label, value, onChange, t }) {
  return (
    <TouchableOpacity style={[styles.toggle, { borderColor: t.border }]} onPress={() => onChange(!value)}>
      <Text style={{ color: t.text }}>{label}</Text>
      <Text style={{ color: value ? palette.green : t.sub, fontWeight: "800" }}>{value ? "Actif" : "Inactif"}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  h1: { fontSize: 24, fontWeight: "800", marginBottom: 8 },
  sectionBox: { borderWidth: 1, borderRadius: 8, padding: 14, marginTop: 14 },
  section: { fontWeight: "800", fontSize: 16, marginBottom: 4 },
  input: { borderWidth: 1, borderRadius: 8, padding: 12 },
  saveBtn: { backgroundColor: palette.blue, padding: 12, borderRadius: 8, alignItems: "center", marginTop: 12 },
  modeRow: { flexDirection: "row", justifyContent: "space-between", borderWidth: 1, borderRadius: 8, padding: 12, marginTop: 8 },
  hint: { fontSize: 11, marginTop: 6 },
  logout: { marginTop: 24, marginBottom: 30, padding: 14, alignItems: "center" },
  badges: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 12 },
  segmented: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 10, marginBottom: 10 },
  segment: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8 },
  toggle: { borderWidth: 1, borderRadius: 8, padding: 12, marginTop: 8, flexDirection: "row", justifyContent: "space-between" },
  message: { color: palette.green, marginTop: 12, fontWeight: "700" },
  error: { color: palette.danger, marginTop: 12, fontWeight: "700" },
});
