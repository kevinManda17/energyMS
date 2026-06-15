import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView } from "react-native";
import { authApi } from "../api/endpoints";
import { useAuthStore } from "../store/auth";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

export default function RegisterScreen({ navigation }) {
  const t = useTheme();
  const login = useAuthStore((s) => s.login);
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");

  const set = (k) => (v) => setForm({ ...form, [k]: v });

  async function onSubmit() {
    setError("");
    try {
      await authApi.register(form);
      await login(form.username, form.password);
    } catch (e) {
      const data = e.response?.data;
      setError(data ? Object.values(data).flat().join(" ") : "Erreur.");
    }
  }

  return (
    <ScrollView style={{ backgroundColor: t.bg }} contentContainerStyle={styles.container}>
      <Text style={[styles.title, { color: t.text }]}>Créer un compte</Text>
      {["username", "email", "password"].map((k) => (
        <View key={k}>
          <Text style={[styles.label, { color: t.text }]}>
            {k === "username" ? "Identifiant" : k === "email" ? "E-mail" : "Mot de passe"}
          </Text>
          <TextInput
            style={[styles.input, { color: t.text, borderColor: t.border }]}
            value={form[k]}
            onChangeText={set(k)}
            secureTextEntry={k === "password"}
            autoCapitalize="none"
          />
        </View>
      ))}
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <TouchableOpacity style={styles.button} onPress={onSubmit}>
        <Text style={styles.buttonText}>Créer mon compte</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => navigation.goBack()}>
        <Text style={[styles.link, { color: palette.blue }]}>Retour</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, paddingTop: 60 },
  title: { fontSize: 24, fontWeight: "800", marginBottom: 16 },
  label: { fontSize: 13, fontWeight: "600", marginBottom: 6, marginTop: 12 },
  input: { borderWidth: 1, borderRadius: 12, padding: 12, fontSize: 15 },
  button: { backgroundColor: palette.blue, padding: 14, borderRadius: 12, marginTop: 20, alignItems: "center" },
  buttonText: { color: "#fff", fontWeight: "700" },
  link: { textAlign: "center", marginTop: 16 },
  error: { color: palette.danger, marginTop: 12 },
});
