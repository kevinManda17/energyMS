import { useState } from "react";
import { Text, TouchableOpacity, StyleSheet, View } from "react-native";
import { LockKeyhole, LogIn, User, UserPlus } from "lucide-react-native";
import { FormInput } from "../components/FormInput";
import { Screen } from "../components/Screen";
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
    <Screen style={styles.container}>
      <View style={styles.brand}>
        <Text style={styles.logo}>EMS</Text>
        <Text style={[styles.subtitle, { color: t.sub }]}>Energy Management System</Text>
      </View>

      <View style={styles.form}>
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
          placeholder="ex: demo12345"
          secureTextEntry
          textContentType="password"
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <TouchableOpacity style={styles.button} onPress={onSubmit} disabled={loading}>
          <LogIn color="#fff" size={18} strokeWidth={2.4} />
          <Text style={styles.buttonText}>{loading ? "Connexion..." : "Se connecter"}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryLink} onPress={() => navigation.navigate("Register")}>
          <UserPlus color={palette.blue} size={17} strokeWidth={2.4} />
          <Text style={[styles.link, { color: palette.blue }]}>Creer un compte</Text>
        </TouchableOpacity>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: { justifyContent: "center", paddingHorizontal: 24 },
  brand: { alignItems: "center", marginBottom: 22 },
  logo: { fontSize: 42, fontWeight: "800", color: palette.blue, textAlign: "center" },
  subtitle: { textAlign: "center", marginTop: 4 },
  form: { width: "100%" },
  button: {
    backgroundColor: palette.blue,
    padding: 14,
    borderRadius: 8,
    marginTop: 22,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 8,
  },
  buttonText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  secondaryLink: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 7, marginTop: 18 },
  link: { textAlign: "center", fontWeight: "800" },
  error: { color: palette.danger, marginTop: 12 },
});
