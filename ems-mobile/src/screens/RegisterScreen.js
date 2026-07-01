import React, { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  KeyRound,
  LockKeyhole,
  Mail,
  Phone,
  Send,
  ShieldCheck,
  User,
  UserPlus,
  Zap,
} from "lucide-react-native";
import { FormInput } from "../components/FormInput";
import { authApi } from "../api/endpoints";
import { useAuthStore } from "../store/auth";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

const STEPS = [
  { label: "Identité" },
  { label: "Téléphone" },
  { label: "Vérif." },
  { label: "Mot de passe" },
  { label: "Confirmation" },
];

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
      setError("Veuillez compléter tous les champs.");
      return;
    }
    setError("");
    setStep(1);
  }

  async function sendCode() {
    setError("");
    setNotice("");
    if (!validPhone(form.phone)) {
      setError("Numéro de téléphone invalide.");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.sendPhoneCode({ phone: form.phone });
      setNotice(res.dev_code ? `Code de test: ${res.dev_code}` : "Code envoyé par SMS.");
      setStep(2);
    } catch {
      setError("Envoi impossible. Vérifiez le numéro.");
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
      setNotice("Numéro vérifié avec succès !");
      setStep(3);
    } catch {
      setError("Code invalide ou expiré.");
    } finally {
      setLoading(false);
    }
  }

  function nextPassword() {
    setError("");
    if (!validPassword(form.password)) {
      setError("Mot de passe trop faible (min. 8 caractères, une lettre et un chiffre).");
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
      setError("Création du compte impossible. Réessayez.");
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
        {/* Header */}
        <View style={[styles.header, { backgroundColor: palette.blue }]}>
          <View style={styles.headerBgCircle} />
          <View style={styles.logoRow}>
            <View style={styles.logoIcon}>
              <Zap color="#fff" size={22} strokeWidth={2.6} />
            </View>
            <Text style={styles.logoText}>EMS</Text>
          </View>
          <Text style={styles.headerTitle}>Créer un compte</Text>
        </View>

        {/* Stepper */}
        <View style={[styles.stepperWrap, { backgroundColor: t.card, borderColor: t.border }]}>
          {STEPS.map((s, i) => {
            const done = i < step;
            const active = i === step;
            return (
              <React.Fragment key={i}>
                <View style={styles.stepItem}>
                  <View
                    style={[
                      styles.stepDot,
                      done && { backgroundColor: palette.green, borderColor: palette.green },
                      active && { backgroundColor: palette.blue, borderColor: palette.blue },
                      !done && !active && { backgroundColor: "transparent", borderColor: t.border },
                    ]}
                  >
                    {done ? (
                      <CheckCircle color="#fff" size={12} strokeWidth={2.8} />
                    ) : (
                      <Text style={[styles.stepNum, { color: active ? "#fff" : t.sub }]}>
                        {i + 1}
                      </Text>
                    )}
                  </View>
                  <Text
                    style={[
                      styles.stepLabel,
                      { color: active ? palette.blue : done ? palette.green : t.sub },
                    ]}
                    numberOfLines={1}
                  >
                    {s.label}
                  </Text>
                </View>
                {i < STEPS.length - 1 && (
                  <View style={[styles.stepLine, { backgroundColor: i < step ? palette.green : t.border }]} />
                )}
              </React.Fragment>
            );
          })}
        </View>

        {/* Form card */}
        <View style={[styles.card, { backgroundColor: t.card, shadowColor: t.text }]}>
          <Text style={[styles.stepTitle, { color: t.text }]}>{STEPS[step].label}</Text>

          {step === 0 && (
            <>
              <FormInput label="Prénom" icon={User} value={form.first_name} onChangeText={set("first_name")} placeholder="ex: Kevin" />
              <FormInput label="Nom de famille" icon={User} value={form.last_name} onChangeText={set("last_name")} placeholder="ex: Manda" />
              <FormInput label="Identifiant" icon={User} value={form.username} onChangeText={set("username")} placeholder="ex: kevin_manda" />
              <FormInput label="Adresse e-mail" icon={Mail} value={form.email} onChangeText={set("email")} placeholder="ex: kevin@email.com" keyboardType="email-address" />
              <PrimaryBtn label="Continuer" Icon={ArrowRight} onPress={nextPersonal} loading={false} />
            </>
          )}

          {step === 1 && (
            <>
              <Text style={[styles.stepHint, { color: t.sub }]}>
                Un code de vérification sera envoyé par SMS à ce numéro.
              </Text>
              <FormInput label="Numéro de téléphone" icon={Phone} value={form.phone} onChangeText={set("phone")} placeholder="ex: +243 81 234 5678" keyboardType="phone-pad" />
              <PrimaryBtn label={loading ? "Envoi..." : "Envoyer le code"} Icon={Send} onPress={sendCode} loading={loading} />
              <BackBtn onPress={() => setStep(0)} />
            </>
          )}

          {step === 2 && (
            <>
              <Text style={[styles.stepHint, { color: t.sub }]}>
                Entrez le code à 6 chiffres reçu sur {form.phone}
              </Text>
              <FormInput label="Code de vérification" icon={KeyRound} value={form.code} onChangeText={set("code")} placeholder="ex: 123456" keyboardType="number-pad" />
              <PrimaryBtn label={loading ? "Vérification..." : "Vérifier le code"} Icon={ShieldCheck} onPress={verifyCode} loading={loading} />
              <TouchableOpacity onPress={sendCode} style={styles.resendBtn}>
                <Text style={{ color: palette.blue, fontWeight: "700", fontSize: 13 }}>
                  Renvoyer le code
                </Text>
              </TouchableOpacity>
              <BackBtn onPress={() => setStep(1)} />
            </>
          )}

          {step === 3 && (
            <>
              <Text style={[styles.stepHint, { color: t.sub }]}>
                Choisissez un mot de passe sécurisé (min. 8 caractères).
              </Text>
              <FormInput label="Mot de passe" icon={LockKeyhole} value={form.password} onChangeText={set("password")} placeholder="••••••••" secureTextEntry />
              <FormInput label="Confirmation" icon={LockKeyhole} value={form.password_confirm} onChangeText={set("password_confirm")} placeholder="Répétez le mot de passe" secureTextEntry />
              <PrimaryBtn label="Continuer" Icon={ArrowRight} onPress={nextPassword} loading={false} />
              <BackBtn onPress={() => setStep(2)} />
            </>
          )}

          {step === 4 && (
            <>
              <Text style={[styles.stepHint, { color: t.sub }]}>
                Vérifiez vos informations avant de créer le compte.
              </Text>
              {[
                { label: "Prénom", value: form.first_name },
                { label: "Nom", value: form.last_name },
                { label: "Identifiant", value: form.username },
                { label: "E-mail", value: form.email },
                { label: "Téléphone", value: form.phone },
              ].map((row) => (
                <SummaryRow key={row.label} label={row.label} value={row.value} t={t} />
              ))}
              <PrimaryBtn
                label={loading ? "Création en cours..." : "Créer mon compte"}
                Icon={UserPlus}
                onPress={createAccount}
                loading={loading}
              />
              <BackBtn onPress={() => setStep(3)} />
            </>
          )}

          {notice ? (
            <View style={styles.noticeBox}>
              <CheckCircle color={palette.green} size={15} strokeWidth={2.4} />
              <Text style={styles.noticeText}>{notice}</Text>
            </View>
          ) : null}
          {error ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}
        </View>

        <TouchableOpacity style={styles.loginLink} onPress={() => navigation.goBack()}>
          <ArrowLeft color={palette.blue} size={15} strokeWidth={2.4} />
          <Text style={{ color: palette.blue, fontWeight: "700", fontSize: 13 }}>
            Retour à la connexion
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function PrimaryBtn({ label, Icon, onPress, loading }) {
  return (
    <TouchableOpacity
      style={[styles.primaryBtn, loading && styles.primaryBtnDisabled]}
      onPress={onPress}
      disabled={loading}
      activeOpacity={0.85}
    >
      {Icon ? <Icon color="#fff" size={17} strokeWidth={2.4} /> : null}
      <Text style={styles.primaryBtnText}>{label}</Text>
    </TouchableOpacity>
  );
}

function BackBtn({ onPress }) {
  return (
    <TouchableOpacity style={styles.backBtn} onPress={onPress}>
      <ArrowLeft color={palette.blue} size={15} strokeWidth={2.4} />
      <Text style={{ color: palette.blue, fontWeight: "700", fontSize: 13 }}>Retour</Text>
    </TouchableOpacity>
  );
}

function SummaryRow({ label, value, t }) {
  return (
    <View style={[styles.summaryRow, { borderColor: t.border }]}>
      <Text style={{ color: t.sub, fontSize: 12, width: 90 }}>{label}</Text>
      <Text style={{ color: t.text, fontWeight: "700", flex: 1 }}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 1 },

  header: {
    paddingTop: 52,
    paddingBottom: 28,
    alignItems: "center",
    overflow: "hidden",
  },
  headerBgCircle: {
    position: "absolute",
    top: -80,
    right: -80,
    width: 220,
    height: 220,
    borderRadius: 110,
    backgroundColor: "rgba(255,255,255,0.07)",
  },
  logoRow: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 10 },
  logoIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.18)",
    alignItems: "center",
    justifyContent: "center",
  },
  logoText: { color: "#fff", fontSize: 28, fontWeight: "800", letterSpacing: 1.5 },
  headerTitle: { color: "rgba(255,255,255,0.9)", fontSize: 16, fontWeight: "600" },

  stepperWrap: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: 16,
    marginTop: -1,
    paddingHorizontal: 12,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderBottomLeftRadius: 0,
    borderBottomRightRadius: 0,
  },
  stepItem: { alignItems: "center", flex: 1 },
  stepDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  stepNum: { fontSize: 10, fontWeight: "800" },
  stepLabel: { fontSize: 9, fontWeight: "700", textAlign: "center" },
  stepLine: { flex: 1, height: 2, marginBottom: 16 },

  card: {
    marginHorizontal: 16,
    marginTop: 0,
    borderRadius: 0,
    borderBottomLeftRadius: 16,
    borderBottomRightRadius: 16,
    padding: 24,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 4,
  },
  stepTitle: { fontSize: 20, fontWeight: "800", marginBottom: 4 },
  stepHint: { fontSize: 13, lineHeight: 19, marginBottom: 4 },

  primaryBtn: {
    backgroundColor: palette.blue,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
    marginTop: 20,
  },
  primaryBtnDisabled: { opacity: 0.6 },
  primaryBtnText: { color: "#fff", fontWeight: "800", fontSize: 15 },

  backBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginTop: 14,
    paddingVertical: 8,
  },

  resendBtn: {
    alignItems: "center",
    marginTop: 12,
    paddingVertical: 6,
  },

  summaryRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 11,
    borderBottomWidth: 1,
    gap: 8,
  },

  noticeBox: {
    marginTop: 14,
    backgroundColor: palette.greenLight,
    borderWidth: 1,
    borderColor: "#86EFAC",
    borderRadius: 10,
    padding: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  noticeText: { color: palette.green, fontSize: 13, fontWeight: "600", flex: 1 },

  errorBox: {
    marginTop: 14,
    backgroundColor: palette.dangerLight,
    borderWidth: 1,
    borderColor: "#FCA5A5",
    borderRadius: 10,
    padding: 12,
  },
  errorText: { color: palette.danger, fontSize: 13, fontWeight: "600" },

  loginLink: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    padding: 20,
    paddingTop: 14,
  },
});
