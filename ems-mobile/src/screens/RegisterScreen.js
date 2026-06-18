import { useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { ArrowRight, KeyRound, LockKeyhole, Mail, Phone, Send, ShieldCheck, User, UserPlus } from "lucide-react-native";
import { FormInput } from "../components/FormInput";
import { ScreenScroll } from "../components/Screen";
import { authApi } from "../api/endpoints";
import { useAuthStore } from "../store/auth";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

const initialForm = {
  first_name: "",
  last_name: "",
  username: "",
  email: "",
  phone: "",
  code: "",
  password: "",
  password_confirm: "",
  phone_verification_token: null,
};

function validPhone(phone) {
  return /^[0-9+()\s-]{8,}$/.test(phone.trim());
}

function validPassword(password) {
  return password.length >= 8 && /[A-Za-z]/.test(password) && /\d/.test(password);
}

export default function RegisterScreen({ navigation }) {
  const t = useTheme();
  const login = useAuthStore((s) => s.login);
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k) => (v) => setForm({ ...form, [k]: v });

  function nextPersonal() {
    if (!form.first_name || !form.last_name || !form.username || !form.email) {
      setError("Completez les informations.");
      return;
    }
    setError("");
    setStep(1);
  }

  async function sendCode() {
    setError("");
    setNotice("");
    if (!validPhone(form.phone)) {
      setError("Numero invalide.");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.sendPhoneCode({ phone: form.phone });
      setNotice(res.dev_code ? `Code de test: ${res.dev_code}` : "Code envoye.");
      setStep(2);
    } catch {
      setError("Envoi impossible.");
    } finally {
      setLoading(false);
    }
  }

  async function verifyCode() {
    setLoading(true);
    setError("");
    try {
      const res = await authApi.verifyPhoneCode({ phone: form.phone, code: form.code });
      setForm({ ...form, phone_verification_token: res.phone_verification_token });
      setNotice("Numero verifie.");
      setStep(3);
    } catch {
      setError("Code invalide ou expire.");
    } finally {
      setLoading(false);
    }
  }

  function nextPassword() {
    setError("");
    if (!validPassword(form.password)) {
      setError("Mot de passe trop faible.");
      return;
    }
    if (form.password !== form.password_confirm) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }
    setStep(4);
  }

  async function createAccount() {
    setLoading(true);
    setError("");
    try {
      await authApi.register({
        first_name: form.first_name,
        last_name: form.last_name,
        username: form.username,
        email: form.email,
        phone: form.phone,
        phone_verification_token: form.phone_verification_token,
        password: form.password,
        password_confirm: form.password_confirm,
      });
      await login(form.username, form.password);
    } catch {
      setError("Creation impossible.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScreenScroll>
      <Text style={[styles.title, { color: t.text }]}>Creer un compte</Text>
      <Text style={[styles.stepText, { color: t.sub }]}>Etape {step + 1} sur 5</Text>

      {step === 0 && (
        <>
          <FormInput label="Prenom" icon={User} value={form.first_name} onChangeText={set("first_name")} placeholder="ex: Kevin" />
          <FormInput label="Nom" icon={User} value={form.last_name} onChangeText={set("last_name")} placeholder="ex: Manda" />
          <FormInput label="Identifiant" icon={User} value={form.username} onChangeText={set("username")} placeholder="ex: kevin_manda" />
          <FormInput label="E-mail" icon={Mail} value={form.email} onChangeText={set("email")} placeholder="ex: kevin@email.com" keyboardType="email-address" />
          <Button label="Continuer" Icon={ArrowRight} onPress={nextPersonal} />
        </>
      )}

      {step === 1 && (
        <>
          <FormInput label="Telephone" icon={Phone} value={form.phone} onChangeText={set("phone")} placeholder="ex: +243 81 234 5678" keyboardType="phone-pad" />
          <Button label={loading ? "Envoi..." : "Envoyer le code"} Icon={Send} onPress={sendCode} />
          <Back onPress={() => setStep(0)} />
        </>
      )}

      {step === 2 && (
        <>
          <FormInput label="Code de verification" icon={KeyRound} value={form.code} onChangeText={set("code")} placeholder="ex: 123456" keyboardType="number-pad" />
          <Button label={loading ? "Verification..." : "Verifier"} Icon={ShieldCheck} onPress={verifyCode} />
          <TouchableOpacity onPress={sendCode}>
            <Text style={[styles.link, { color: palette.blue }]}>Renvoyer le code</Text>
          </TouchableOpacity>
          <Back onPress={() => setStep(1)} />
        </>
      )}

      {step === 3 && (
        <>
          <FormInput label="Mot de passe" icon={LockKeyhole} value={form.password} onChangeText={set("password")} placeholder="ex: Energie2026" secureTextEntry />
          <FormInput label="Confirmation" icon={LockKeyhole} value={form.password_confirm} onChangeText={set("password_confirm")} placeholder="Repetez le mot de passe" secureTextEntry />
          <Text style={{ color: t.sub, fontSize: 12, marginTop: 8 }}>Minimum 8 caracteres, une lettre et un chiffre.</Text>
          <Button label="Continuer" Icon={ArrowRight} onPress={nextPassword} />
          <Back onPress={() => setStep(2)} />
        </>
      )}

      {step === 4 && (
        <View>
          <Summary label="Nom" value={`${form.first_name} ${form.last_name}`} t={t} />
          <Summary label="Identifiant" value={form.username} t={t} />
          <Summary label="E-mail" value={form.email} t={t} />
          <Summary label="Telephone" value={form.phone} t={t} />
          <Button label={loading ? "Creation..." : "Creer mon compte"} Icon={UserPlus} onPress={createAccount} />
          <Back onPress={() => setStep(3)} />
        </View>
      )}

      {notice ? <Text style={styles.notice}>{notice}</Text> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TouchableOpacity onPress={() => navigation.goBack()}>
        <Text style={[styles.link, { color: palette.blue }]}>Retour connexion</Text>
      </TouchableOpacity>
    </ScreenScroll>
  );
}

function Button({ label, Icon, onPress }) {
  return (
    <TouchableOpacity style={styles.button} onPress={onPress}>
      {Icon ? <Icon color="#fff" size={18} strokeWidth={2.4} /> : null}
      <Text style={styles.buttonText}>{label}</Text>
    </TouchableOpacity>
  );
}

function Back({ onPress }) {
  return (
    <TouchableOpacity onPress={onPress}>
      <Text style={[styles.link, { color: palette.blue }]}>Retour</Text>
    </TouchableOpacity>
  );
}

function Summary({ label, value, t }) {
  return (
    <View style={[styles.summary, { borderColor: t.border }]}>
      <Text style={{ color: t.sub }}>{label}</Text>
      <Text style={{ color: t.text, fontWeight: "700" }}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 28, fontWeight: "800", lineHeight: 34 },
  stepText: { marginTop: 4, marginBottom: 10 },
  button: {
    backgroundColor: palette.blue,
    padding: 14,
    borderRadius: 8,
    marginTop: 20,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 8,
  },
  buttonText: { color: "#fff", fontWeight: "800" },
  link: { textAlign: "center", marginTop: 16, fontWeight: "800" },
  error: { color: palette.danger, marginTop: 12 },
  notice: { color: palette.green, marginTop: 12, fontWeight: "700" },
  summary: { borderBottomWidth: 1, paddingVertical: 10 },
});
