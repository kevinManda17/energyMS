import { useEffect, useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { storage } from "../storage";
import { API_PRESETS } from "../api/config";
import { useAuthStore } from "../store/auth";

const MODES = [
  { id: "cloud", label: "Cloud (API distante)" },
  { id: "edge", label: "Edge (Raspberry Pi / LAN)" },
  { id: "local", label: "Local (URL personnalisée)" },
];

export default function SettingsScreen() {
  const t = useTheme();
  const { user, logout } = useAuthStore();
  const [mode, setMode] = useState("cloud");
  const [custom, setCustom] = useState("");

  useEffect(() => {
    storage.getApiMode().then(setMode);
    storage.getCustomUrl().then((u) => setCustom(u || ""));
  }, []);

  async function selectMode(id) {
    setMode(id);
    await storage.setApiMode(id);
  }
  async function saveCustom() {
    await storage.setCustomUrl(custom);
  }

  return (
    <View style={{ flex: 1, backgroundColor: t.bg, padding: 16 }}>
      <Text style={[styles.h1, { color: t.text }]}>Paramètres</Text>

      <Text style={[styles.section, { color: t.sub }]}>Compte</Text>
      <Text style={{ color: t.text }}>{user?.username} · {user?.role}</Text>

      <Text style={[styles.section, { color: t.sub }]}>Mode API</Text>
      {MODES.map((m) => (
        <TouchableOpacity
          key={m.id}
          style={[
            styles.modeRow,
            { borderColor: mode === m.id ? palette.blue : t.border },
          ]}
          onPress={() => selectMode(m.id)}
        >
          <Text style={{ color: t.text }}>{m.label}</Text>
          {mode === m.id && <Text style={{ color: palette.blue }}>✓</Text>}
        </TouchableOpacity>
      ))}

      <Text style={[styles.hint, { color: t.sub }]}>
        Cloud : {API_PRESETS.cloud}{"\n"}Edge : {API_PRESETS.edge}
      </Text>

      {mode === "local" && (
        <View>
          <TextInput
            style={[styles.input, { color: t.text, borderColor: t.border }]}
            value={custom}
            onChangeText={setCustom}
            placeholder="http://172.20.10.2:8000/api"
            placeholderTextColor={t.sub}
            autoCapitalize="none"
          />
          <TouchableOpacity style={styles.saveBtn} onPress={saveCustom}>
            <Text style={{ color: "#fff", fontWeight: "600" }}>Enregistrer l'URL</Text>
          </TouchableOpacity>
        </View>
      )}

      <TouchableOpacity style={styles.logout} onPress={logout}>
        <Text style={{ color: palette.danger, fontWeight: "700" }}>Déconnexion</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  h1: { fontSize: 24, fontWeight: "800", marginBottom: 8 },
  section: { marginTop: 20, marginBottom: 8, fontWeight: "600", fontSize: 12, textTransform: "uppercase" },
  modeRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
  },
  hint: { fontSize: 11, marginTop: 6 },
  input: { borderWidth: 1, borderRadius: 12, padding: 12, marginTop: 10 },
  saveBtn: { backgroundColor: palette.blue, padding: 12, borderRadius: 12, alignItems: "center", marginTop: 8 },
  logout: { marginTop: 32, padding: 14, alignItems: "center" },
});
