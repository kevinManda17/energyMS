import { useState } from "react";
import { ScrollView, View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";
import { Eye, EyeOff, Lock, ShieldCheck } from "lucide-react-native";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { authApi } from "../api/endpoints";

export default function PasswordScreen() {
  const t = useTheme();
  const [fields, setFields] = useState({
    current_password: "",
    new_password: "",
    password_confirm: "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function flash(msg, isError = false) {
    if (isError) { setError(msg); setMessage(""); }
    else          { setMessage(msg); setError(""); }
    setTimeout(() => { setMessage(""); setError(""); }, 3500);
  }

  async function changePassword() {
    if (!fields.current_password || !fields.new_password || !fields.password_confirm) {
      flash("Veuillez remplir tous les champs.", true);
      return;
    }
    if (fields.new_password !== fields.password_confirm) {
      flash("Les deux nouveaux mots de passe ne correspondent pas.", true);
      return;
    }
    if (fields.new_password.length < 8) {
      flash("Le nouveau mot de passe doit contenir au moins 8 caractères.", true);
      return;
    }
    setLoading(true);
    try {
      await authApi.changePassword(fields);
      setFields({ current_password: "", new_password: "", password_confirm: "" });
      flash("Mot de passe modifié avec succès.");
    } catch {
      flash("Modification impossible. Vérifiez votre mot de passe actuel.", true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView
      style={{ backgroundColor: t.bg }}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      {/* Illustration */}
      <View style={[styles.iconBlock, { backgroundColor: palette.purple + "14" }]}>
        <ShieldCheck color={palette.purple} size={38} strokeWidth={1.8} />
      </View>

      {message ? <Toast text={message} color={palette.green} /> : null}
      {error   ? <Toast text={error}   color={palette.danger} /> : null}

      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.cardTitle, { color: t.text }]}>Changer le mot de passe</Text>
        <Text style={[styles.cardSub, { color: t.sub }]}>
          Utilisez un mot de passe fort de minimum 8 caractères avec lettres et chiffres.
        </Text>

        <PasswordField
          label="Mot de passe actuel"
          value={fields.current_password}
          onChangeText={(v) => setFields((f) => ({ ...f, current_password: v }))}
          placeholder="Entrez votre mot de passe actuel"
          t={t}
        />
        <PasswordField
          label="Nouveau mot de passe"
          value={fields.new_password}
          onChangeText={(v) => setFields((f) => ({ ...f, new_password: v }))}
          placeholder="Ex : MonNouveauM0tD3Passe!"
          t={t}
        />
        <PasswordField
          label="Confirmation"
          value={fields.password_confirm}
          onChangeText={(v) => setFields((f) => ({ ...f, password_confirm: v }))}
          placeholder="Répétez le nouveau mot de passe"
          t={t}
        />

        <TouchableOpacity
          style={[styles.saveBtn, { backgroundColor: palette.purple, opacity: loading ? 0.7 : 1 }]}
          onPress={changePassword}
          disabled={loading}
          activeOpacity={0.85}
        >
          <Lock color="#fff" size={16} strokeWidth={2.4} />
          <Text style={{ color: "#fff", fontWeight: "700", fontSize: 14 }}>
            {loading ? "Modification…" : "Modifier le mot de passe"}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Conseils sécurité */}
      <View style={[styles.tipsCard, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.tipsTitle, { color: t.text }]}>Conseils</Text>
        {[
          "Minimum 8 caractères",
          "Mélangez lettres majuscules et minuscules",
          "Ajoutez des chiffres et symboles",
          "Ne réutilisez pas un ancien mot de passe",
        ].map((tip, i) => (
          <View key={i} style={styles.tipRow}>
            <View style={[styles.tipDot, { backgroundColor: palette.purple }]} />
            <Text style={{ color: t.sub, fontSize: 13 }}>{tip}</Text>
          </View>
        ))}
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

function PasswordField({ label, value, onChangeText, placeholder, t }) {
  const [hidden, setHidden] = useState(true);
  return (
    <View style={{ marginTop: 14 }}>
      <Text style={[styles.fieldLabel, { color: t.sub }]}>{label}</Text>
      <View style={[styles.inputWrap, { borderColor: t.border }]}>
        <Lock color={t.sub} size={15} strokeWidth={2.2} style={{ marginRight: 8 }} />
        <TextInput
          style={[styles.input, { color: t.text }]}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={t.sub}
          secureTextEntry={hidden}
          textContentType="password"
          autoCapitalize="none"
          autoCorrect={false}
          selectionColor={palette.purple}
        />
        <TouchableOpacity onPress={() => setHidden((v) => !v)} style={styles.eyeBtn}>
          {hidden
            ? <Eye color={palette.purple} size={17} strokeWidth={2.2} />
            : <EyeOff color={palette.purple} size={17} strokeWidth={2.2} />}
        </TouchableOpacity>
      </View>
    </View>
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
  cardTitle: { fontSize: 16, fontWeight: "800", marginBottom: 4 },
  cardSub: { fontSize: 13, lineHeight: 18, marginBottom: 4 },

  fieldLabel: { fontSize: 12, marginBottom: 5 },
  inputWrap: {
    borderWidth: 1, borderRadius: 10, minHeight: 48,
    paddingHorizontal: 12, flexDirection: "row", alignItems: "center",
  },
  input: { flex: 1, paddingVertical: 10, fontSize: 14, backgroundColor: "transparent" },
  eyeBtn: { width: 36, height: 36, alignItems: "center", justifyContent: "center" },

  saveBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, padding: 14, borderRadius: 10, marginTop: 18,
  },

  tipsCard: { marginHorizontal: 14, marginTop: 14, borderRadius: 14, borderWidth: 1, padding: 16 },
  tipsTitle: { fontSize: 14, fontWeight: "800", marginBottom: 10 },
  tipRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 8 },
  tipDot: { width: 6, height: 6, borderRadius: 3 },
});
