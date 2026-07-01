import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { LockKeyhole, LogIn, User, UserPlus, Zap } from "lucide-react-native";
import { FormInput } from "../components/FormInput";
import { useAuthStore } from "../store/auth";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

export default function LoginScreen({ navigation }) {
  const t = useTheme();
  const login = useAuthStore((s) => s.login);
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo12345");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit() {
    setError("");
    setLoading(true);
    try {
      await login(username, password);
    } catch {
      setError("Identifiants invalides. Vérifiez votre nom d'utilisateur et mot de passe.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        style={{ backgroundColor: t.bg }}
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* Hero header */}
        <View style={styles.hero}>
          <View style={[styles.heroBg, { backgroundColor: palette.blue }]}>
            <View style={styles.heroBgAccent} />
          </View>
          <View style={styles.logoWrap}>
            <View style={styles.logoCircle}>
              <Zap color="#fff" size={30} strokeWidth={2.6} />
            </View>
            <Text style={styles.logoText}>EMS</Text>
          </View>
          <Text style={styles.tagline}>Energy Management System</Text>
          <Text style={styles.taglineSub}>Kinshasa · Goma · Lubumbashi</Text>
        </View>

        {/* Form card */}
        <View style={[styles.card, { backgroundColor: t.card, shadowColor: t.text }]}>
          <Text style={[styles.cardTitle, { color: t.text }]}>Connexion</Text>
          <Text style={[styles.cardSub, { color: t.sub }]}>
            Accédez à votre tableau de bord énergie
          </Text>

          <FormInput
            label="Identifiant"
            icon={User}
            value={username}
            onChangeText={setUsername}
            placeholder="ex: demo"
            textContentType="username"
          />
          <FormInput
            label="Mot de passe"
            icon={LockKeyhole}
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            secureTextEntry
            textContentType="password"
          />

          {error ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <TouchableOpacity
            style={[styles.primaryBtn, loading && styles.primaryBtnDisabled]}
            onPress={onSubmit}
            disabled={loading}
            activeOpacity={0.85}
          >
            <LogIn color="#fff" size={18} strokeWidth={2.4} />
            <Text style={styles.primaryBtnText}>
              {loading ? "Connexion en cours..." : "Se connecter"}
            </Text>
          </TouchableOpacity>

          <View style={styles.divider}>
            <View style={[styles.divLine, { backgroundColor: t.border }]} />
            <Text style={[styles.divText, { color: t.sub }]}>ou</Text>
            <View style={[styles.divLine, { backgroundColor: t.border }]} />
          </View>

          <TouchableOpacity
            style={[styles.secondaryBtn, { borderColor: palette.blue }]}
            onPress={() => navigation.navigate("Register")}
            activeOpacity={0.8}
          >
            <UserPlus color={palette.blue} size={17} strokeWidth={2.4} />
            <Text style={[styles.secondaryBtnText, { color: palette.blue }]}>
              Créer un compte
            </Text>
          </TouchableOpacity>
        </View>

        <Text style={[styles.footer, { color: t.sub }]}>
          Système de gestion d'énergie solaire © 2025
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 1 },

  hero: {
    height: 240,
    alignItems: "center",
    justifyContent: "flex-end",
    paddingBottom: 32,
    overflow: "hidden",
  },
  heroBg: {
    ...StyleSheet.absoluteFillObject,
    overflow: "hidden",
  },
  heroBgAccent: {
    position: "absolute",
    top: -60,
    right: -60,
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: "rgba(255,255,255,0.07)",
  },
  logoWrap: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 10 },
  logoCircle: {
    width: 52,
    height: 52,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.18)",
    alignItems: "center",
    justifyContent: "center",
  },
  logoText: { fontSize: 38, fontWeight: "800", color: "#fff", letterSpacing: 2 },
  tagline: { color: "rgba(255,255,255,0.92)", fontSize: 15, fontWeight: "600" },
  taglineSub: { color: "rgba(255,255,255,0.6)", fontSize: 12, marginTop: 4 },

  card: {
    margin: 16,
    marginTop: -24,
    borderRadius: 20,
    padding: 24,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 16,
    elevation: 6,
  },
  cardTitle: { fontSize: 22, fontWeight: "800", marginBottom: 4 },
  cardSub: { fontSize: 13, marginBottom: 4 },

  errorBox: {
    marginTop: 14,
    backgroundColor: palette.dangerLight,
    borderWidth: 1,
    borderColor: "#FCA5A5",
    borderRadius: 10,
    padding: 12,
  },
  errorText: { color: palette.danger, fontSize: 13, fontWeight: "600" },

  primaryBtn: {
    backgroundColor: palette.blue,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 15,
    borderRadius: 12,
    marginTop: 20,
  },
  primaryBtnDisabled: { opacity: 0.6 },
  primaryBtnText: { color: "#fff", fontWeight: "800", fontSize: 15 },

  divider: { flexDirection: "row", alignItems: "center", gap: 10, marginVertical: 18 },
  divLine: { flex: 1, height: 1 },
  divText: { fontSize: 13 },

  secondaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 13,
    borderRadius: 12,
    borderWidth: 1.5,
  },
  secondaryBtnText: { fontWeight: "700", fontSize: 14 },

  footer: { textAlign: "center", fontSize: 11, padding: 20, paddingTop: 8 },
});
