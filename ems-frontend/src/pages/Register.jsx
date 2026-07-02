import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
  Lock,
  Send,
  ShieldCheck,
  UserPlus,
} from "lucide-react";
import AuthShell from "../components/AuthShell";
import { authApi } from "../api/endpoints";
import { useAuthStore } from "../store/auth";

const STEPS = ["Informations", "Téléphone", "Vérification", "Mot de passe", "Récapitulatif"];

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

function errorText(err, fallback) {
  const data = err.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  return Object.values(data).flat().join(" ");
}

function validPhone(phone)    { return /^[0-9+()\s-]{8,}$/.test(phone.trim()); }
function validPassword(pwd)   { return pwd.length >= 8 && /[A-Za-z]/.test(pwd) && /\d/.test(pwd); }

export default function Register() {
  const navigate = useNavigate();
  const login    = useAuthStore((s) => s.login);
  const [step, setStep]                       = useState(0);
  const [form, setForm]                       = useState(initialForm);
  const [error, setError]                     = useState("");
  const [notice, setNotice]                   = useState("");
  const [loading, setLoading]                 = useState(false);
  const [showPassword, setShowPassword]       = useState(false);
  const [showConfirm, setShowConfirm]         = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  function nextPersonal() {
    setError("");
    if (!form.first_name || !form.last_name || !form.username || !form.email) {
      setError("Complétez toutes les informations personnelles.");
      return;
    }
    setStep(1);
  }

  async function sendCode() {
    setError("");
    setNotice("");
    if (!validPhone(form.phone)) {
      setError("Entrez un numéro de téléphone valide.");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.sendPhoneCode({ phone: form.phone });
      setNotice(res.dev_code ? `Code de test : ${res.dev_code}` : "Code envoyé.");
      setStep(2);
    } catch (err) {
      setError(errorText(err, "Impossible d'envoyer le code."));
    } finally {
      setLoading(false);
    }
  }

  async function verifyCode() {
    setError("");
    setNotice("");
    if (!form.code) {
      setError("Entrez le code reçu.");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.verifyPhoneCode({ phone: form.phone, code: form.code });
      setForm({ ...form, phone_verification_token: res.phone_verification_token });
      setNotice("Numéro vérifié avec succès.");
      setStep(3);
    } catch (err) {
      setError(errorText(err, "Code invalide ou expiré."));
    } finally {
      setLoading(false);
    }
  }

  function nextPassword() {
    setError("");
    if (!validPassword(form.password)) {
      setError("Le mot de passe doit contenir au moins 8 caractères, une lettre et un chiffre.");
      return;
    }
    if (form.password !== form.password_confirm) {
      setError("Les deux mots de passe doivent correspondre.");
      return;
    }
    setStep(4);
  }

  async function createAccount() {
    setError("");
    setLoading(true);
    try {
      await authApi.register({
        first_name: form.first_name,
        last_name:  form.last_name,
        username:   form.username,
        email:      form.email,
        phone:      form.phone,
        phone_verification_token: form.phone_verification_token,
        password:         form.password,
        password_confirm: form.password_confirm,
      });
      await login(form.username, form.password);
      navigate("/dashboard");
    } catch (err) {
      setError(errorText(err, "Inscription impossible."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell>
      <div className="card p-8">
        <h1 className="text-2xl font-bold text-navy dark:text-white">Créer un compte</h1>
        <p className="mt-1 text-sm text-slate-500">
          Étape {step + 1} sur {STEPS.length} : {STEPS[step]}
        </p>

        {/* Barre de progression */}
        <div className="mt-5 grid grid-cols-5 gap-1.5">
          {STEPS.map((label, i) => (
            <div
              key={label}
              className={`h-1.5 rounded-full transition-colors ${
                i < step ? "bg-energy" : i === step ? "bg-electric" : "bg-slate-200 dark:bg-white/10"
              }`}
            />
          ))}
        </div>

        <div className="mt-6 space-y-4">
          {step === 0 && (
            <>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Prénom"      value={form.first_name} onChange={set("first_name")} />
                <Field label="Nom"         value={form.last_name}  onChange={set("last_name")}  />
              </div>
              <Field label="Nom d'utilisateur" value={form.username} onChange={set("username")} autoCapitalize="none" />
              <Field label="Adresse e-mail"    type="email" value={form.email} onChange={set("email")} />
              <StepActions onNext={nextPersonal} />
            </>
          )}

          {step === 1 && (
            <>
              <Field
                label="Numéro de téléphone"
                value={form.phone}
                onChange={set("phone")}
                placeholder="+243 81 234 5678"
              />
              <StepActions
                onBack={() => setStep(0)}
                onNext={sendCode}
                nextLabel="Envoyer le code"
                nextIcon={Send}
                loading={loading}
              />
            </>
          )}

          {step === 2 && (
            <>
              <Field
                label="Code de vérification"
                value={form.code}
                onChange={set("code")}
                placeholder="123456"
              />
              <button
                type="button"
                className="text-sm font-semibold text-electric hover:underline"
                onClick={sendCode}
                disabled={loading}
              >
                Renvoyer le code
              </button>
              <StepActions
                onBack={() => setStep(1)}
                onNext={verifyCode}
                nextLabel="Vérifier"
                nextIcon={ShieldCheck}
                loading={loading}
              />
            </>
          )}

          {step === 3 && (
            <>
              <PasswordField
                label="Mot de passe"
                value={form.password}
                onChange={set("password")}
                placeholder="ex: Energie2026"
                visible={showPassword}
                onToggle={() => setShowPassword((v) => !v)}
              />
              <PasswordField
                label="Confirmation du mot de passe"
                value={form.password_confirm}
                onChange={set("password_confirm")}
                placeholder="Répétez le mot de passe"
                visible={showConfirm}
                onToggle={() => setShowConfirm((v) => !v)}
              />
              <p className="text-xs text-slate-500">
                Minimum 8 caractères avec une lettre et un chiffre.
              </p>
              <StepActions onBack={() => setStep(2)} onNext={nextPassword} />
            </>
          )}

          {step === 4 && (
            <>
              <div className="rounded-xl border border-slate-100 p-4 text-sm dark:border-white/10">
                <Summary label="Nom"          value={`${form.first_name} ${form.last_name}`} />
                <Summary label="Identifiant"  value={form.username} />
                <Summary label="E-mail"       value={form.email} />
                <Summary label="Téléphone"    value={form.phone} />
                <Summary label="Vérification" value="Numéro vérifié" />
              </div>
              <StepActions
                onBack={() => setStep(3)}
                onNext={createAccount}
                nextLabel="Créer mon compte"
                nextIcon={UserPlus}
                loading={loading}
              />
            </>
          )}

          {notice && (
            <p className="flex items-center gap-2 text-sm text-energy">
              <CheckCircle2 size={16} /> {notice}
            </p>
          )}
          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger dark:bg-red-500/10">
              {error}
            </p>
          )}
        </div>

        <p className="mt-5 text-center text-sm text-slate-500">
          Vous avez déjà un compte ?{" "}
          <Link to="/login" className="font-semibold text-electric hover:underline">
            Se connecter
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}

function Field({ label, type = "text", value, onChange, placeholder, autoCapitalize }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
        {label}
      </label>
      <input
        type={type}
        className="input"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoCapitalize={autoCapitalize}
        autoComplete="off"
      />
    </div>
  );
}

function PasswordField({ label, value, onChange, placeholder, visible, onToggle }) {
  const Icon = visible ? EyeOff : Eye;
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
        {label}
      </label>
      <div className="relative">
        <Lock className="absolute left-3 top-3 text-slate-400" size={16} />
        <input
          type={visible ? "text" : "password"}
          className="input pl-9 pr-11"
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete="new-password"
        />
        <button
          type="button"
          aria-label={visible ? "Masquer" : "Afficher"}
          className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-electric dark:hover:bg-white/10"
          onClick={onToggle}
        >
          <Icon size={17} />
        </button>
      </div>
    </div>
  );
}

function Summary({ label, value }) {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-2 last:border-0 dark:border-white/10">
      <span className="text-slate-500">{label}</span>
      <span className="font-semibold text-navy dark:text-white">{value}</span>
    </div>
  );
}

function StepActions({ onBack, onNext, nextLabel = "Continuer", nextIcon: NextIcon = ChevronRight, loading }) {
  return (
    <div className="flex items-center justify-between gap-3 pt-2">
      {onBack ? (
        <button type="button" className="btn-ghost" onClick={onBack} disabled={loading}>
          <ChevronLeft size={16} /> Retour
        </button>
      ) : (
        <span />
      )}
      <button type="button" className="btn-primary" onClick={onNext} disabled={loading}>
        <NextIcon size={16} /> {loading ? "Veuillez patienter…" : nextLabel}
      </button>
    </div>
  );
}
