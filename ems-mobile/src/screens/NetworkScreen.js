import { useEffect, useState } from "react";
import { ScrollView, View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";
import { Cloud, Server, Wifi } from "lucide-react-native";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { storage } from "../storage";
import { API_PRESETS } from "../api/config";

const MODES = [
  { id: "cloud", label: "Cloud",      icon: Cloud,  desc: "Serveur de production via Internet" },
  { id: "edge",  label: "Edge",       icon: Wifi,   desc: "Passerelle locale dans le réseau" },
  { id: "local", label: "URL locale", icon: Server, desc: "Adresse IP personnalisée" },
];

export default function NetworkScreen() {
  const t = useTheme();
  const [mode, setMode]   = useState("cloud");
  const [custom, setCustom] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    storage.getApiMode().then(setMode).catch(() => {});
    storage.getCustomUrl().then((u) => setCustom(u || "")).catch(() => {});
  }, []);

  async function selectMode(id) {
    setMode(id);
    await storage.setApiMode(id).catch(() => {});
  }

  async function saveCustom() {
    await storage.setCustomUrl(custom).catch(() => {});
    flash("URL enregistrée.");
  }

  function flash(msg) {
    setMessage(msg);
    setTimeout(() => setMessage(""), 3000);
  }

  const currentUrl =
    mode === "local"
      ? custom || "—"
      : API_PRESETS?.[mode] || "—";

  return (
    <ScrollView
      style={{ backgroundColor: t.bg }}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
    >
      {/* Icon block */}
      <View style={[styles.iconBlock, { backgroundColor: palette.blue + "14" }]}>
        <Wifi color={palette.blue} size={38} strokeWidth={1.8} />
      </View>

      {message ? (
        <View style={[styles.toast, { backgroundColor: palette.green }]}>
          <Text style={styles.toastText}>{message}</Text>
        </View>
      ) : null}

      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.cardTitle, { color: t.text }]}>Mode de connexion</Text>
        <Text style={[styles.cardSub, { color: t.sub }]}>
          Choisissez comment l'application se connecte au backend EMS.
        </Text>

        {MODES.map(({ id, label, icon: Icon, desc }) => {
          const active = mode === id;
          return (
            <TouchableOpacity
              key={id}
              style={[
                styles.modeCard,
                {
                  borderColor: active ? palette.blue : t.border,
                  backgroundColor: active ? palette.blue + "0C" : "transparent",
                },
              ]}
              onPress={() => selectMode(id)}
              activeOpacity={0.8}
            >
              <View style={[styles.modeIcon, { backgroundColor: active ? palette.blue + "18" : t.bg }]}>
                <Icon color={active ? palette.blue : t.sub} size={18} strokeWidth={2.2} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[styles.modeLabel, { color: active ? palette.blue : t.text }]}>
                  {label}
                </Text>
                <Text style={[styles.modeDesc, { color: t.sub }]}>{desc}</Text>
              </View>
              <View style={[styles.radio, { borderColor: active ? palette.blue : t.border }]}>
                {active && <View style={[styles.radioDot, { backgroundColor: palette.blue }]} />}
              </View>
            </TouchableOpacity>
          );
        })}

        {/* Current URL info */}
        <View style={[styles.urlBlock, { backgroundColor: t.bg, borderColor: t.border }]}>
          <Text style={[styles.urlLabel, { color: t.sub }]}>URL active</Text>
          <Text style={[styles.urlValue, { color: t.text }]} numberOfLines={1}>{currentUrl}</Text>
        </View>

        {/* Custom URL input */}
        {mode === "local" && (
          <>
            <Text style={[styles.fieldLabel, { color: t.sub }]}>URL personnalisée</Text>
            <View style={[styles.inputWrap, { borderColor: t.border }]}>
              <Server color={t.sub} size={14} strokeWidth={2.2} style={{ marginRight: 8 }} />
              <TextInput
                style={[styles.input, { color: t.text }]}
                value={custom}
                onChangeText={setCustom}
                placeholder="http://192.168.1.10:8000/api"
                placeholderTextColor={t.sub}
                autoCapitalize="none"
                keyboardType="url"
                selectionColor={palette.blue}
              />
            </View>
            <TouchableOpacity
              style={[styles.saveBtn, { backgroundColor: palette.blue }]}
              onPress={saveCustom}
              activeOpacity={0.85}
            >
              <Text style={{ color: "#fff", fontWeight: "700", fontSize: 14 }}>
                Enregistrer l'URL
              </Text>
            </TouchableOpacity>
          </>
        )}
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
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

  modeCard: {
    flexDirection: "row", alignItems: "center", gap: 12,
    borderWidth: 1.5, borderRadius: 12, padding: 14, marginBottom: 10,
  },
  modeIcon: { width: 36, height: 36, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  modeLabel: { fontSize: 14, fontWeight: "700" },
  modeDesc: { fontSize: 12, marginTop: 2 },
  radio: { width: 20, height: 20, borderRadius: 10, borderWidth: 2, alignItems: "center", justifyContent: "center" },
  radioDot: { width: 10, height: 10, borderRadius: 5 },

  urlBlock: {
    borderWidth: 1, borderRadius: 10, padding: 12, marginTop: 4, marginBottom: 14,
  },
  urlLabel: { fontSize: 11, marginBottom: 4 },
  urlValue: { fontSize: 13, fontWeight: "600" },

  fieldLabel: { fontSize: 12, marginBottom: 6, marginTop: 4 },
  inputWrap: {
    borderWidth: 1, borderRadius: 10, minHeight: 46,
    paddingHorizontal: 12, flexDirection: "row", alignItems: "center",
  },
  input: { flex: 1, paddingVertical: 10, fontSize: 14, backgroundColor: "transparent" },
  saveBtn: { padding: 13, borderRadius: 10, alignItems: "center", marginTop: 12 },
});
