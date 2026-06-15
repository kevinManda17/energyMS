import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";
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
      setError("Identifiants invalides.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={[styles.container, { backgroundColor: t.bg }]}>
      <Text style={styles.logo}>⚡ EMS</Text>
      <Text style={[styles.subtitle, { color: t.sub }]}>
        Energy Management System
      </Text>

      <View style={{ marginTop: 32 }}>
        <Text style={[styles.label, { color: t.text }]}>Identifiant</Text>
        <TextInput
          style={[styles.input, { color: t.text, borderColor: t.border }]}
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
          placeholderTextColor={t.sub}
        />
        <Text style={[styles.label, { color: t.text }]}>Mot de passe</Text>
        <TextInput
          style={[styles.input, { color: t.text, borderColor: t.border }]}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <TouchableOpacity style={styles.button} onPress={onSubmit} disabled={loading}>
          <Text style={styles.buttonText}>
            {loading ? "Connexion…" : "Se connecter"}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => navigation.navigate("Register")}>
          <Text style={[styles.link, { color: palette.blue }]}>
            Pas de compte ? S'inscrire
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24 },
  logo: { fontSize: 40, fontWeight: "800", color: palette.blue, textAlign: "center" },
  subtitle: { textAlign: "center", marginTop: 4 },
  label: { fontSize: 13, fontWeight: "600", marginBottom: 6, marginTop: 12 },
  input: { borderWidth: 1, borderRadius: 12, padding: 12, fontSize: 15 },
  button: {
    backgroundColor: palette.blue,
    padding: 14,
    borderRadius: 12,
    marginTop: 20,
    alignItems: "center",
  },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  link: { textAlign: "center", marginTop: 16 },
  error: { color: palette.danger, marginTop: 12 },
});
