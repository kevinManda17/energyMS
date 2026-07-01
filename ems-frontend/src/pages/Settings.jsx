import { useEffect, useState } from "react";
import {
  Bell,
  Check,
  ChevronRight,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  Mail,
  Monitor,
  Moon,
  Phone,
  Server,
  Shield,
  Sun,
  User,
  Zap,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { Badge } from "../components/ui";
import { authApi, reportsApi } from "../api/endpoints";
import { useAuthStore } from "../store/auth";
import { useUIStore } from "../store/ui";

/* ─────────────────────────────────────────────
   Configuration des onglets
───────────────────────────────────────────── */
const TABS = [
  { id: "profile",       label: "Profil",          icon: User,    color: "electric" },
  { id: "security",      label: "Sécurité",        icon: Lock,    color: "danger" },
  { id: "display",       label: "Affichage",       icon: Eye,     color: "solar" },
  { id: "notifications", label: "Notifications",   icon: Bell,    color: "energy" },
  { id: "api",           label: "API",             icon: Server,  color: "navy" },
  { id: "privacy",       label: "Confidentialité", icon: Shield,  color: "electric" },
];

const TAB_COLORS = {
  electric: { bg: "bg-electric/10", text: "text-electric", border: "border-electric", icon: "text-electric" },
  danger:   { bg: "bg-red-50 dark:bg-red-500/10",  text: "text-danger",   border: "border-danger",   icon: "text-danger" },
  solar:    { bg: "bg-amber-50 dark:bg-amber-500/10", text: "text-solar", border: "border-solar",  icon: "text-solar" },
  energy:   { bg: "bg-green-50 dark:bg-green-500/10", text: "text-energy", border: "border-energy", icon: "text-energy" },
  navy:     { bg: "bg-navy/10",     text: "text-navy dark:text-slate-200",  border: "border-navy",    icon: "text-navy dark:text-slate-300" },
};

const defaultPreferences = {
  language: "fr",
  units: "metric",
  notifications: { critical: true, system: true, reports: false },
};

/* ─────────────────────────────────────────────
   Composant principal
───────────────────────────────────────────── */
export default function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, updateUser } = useAuthStore();
  const { theme, setTheme } = useUIStore();

  const initialTab = TABS.some((t) => t.id === searchParams.get("tab"))
    ? searchParams.get("tab")
    : "profile";

  const [tab, setTabState] = useState(initialTab);
  const [profile, setProfile] = useState({});
  const [preferences, setPreferences] = useState(defaultPreferences);
  const [passwords, setPasswords] = useState({
    current_password: "", new_password: "", password_confirm: "",
  });
  const [toast, setToast] = useState(null); // { type: "success"|"error", msg }

  useEffect(() => {
    setProfile({
      first_name: user?.first_name || "",
      last_name:  user?.last_name  || "",
      email:      user?.email      || "",
      phone:      user?.phone      || "",
    });
    setPreferences({ ...defaultPreferences, ...(user?.preferences || {}) });
  }, [user]);

  useEffect(() => {
    const nextTab = searchParams.get("tab");
    if (TABS.some((t) => t.id === nextTab)) setTabState(nextTab);
  }, [searchParams]);

  function setTab(nextTab) {
    setTabState(nextTab);
    setSearchParams({ tab: nextTab });
  }

  function flash(type, msg) {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3500);
  }

  async function saveProfile() {
    try {
      await updateUser({ ...profile, preferences });
      flash("success", "Profil enregistré avec succès.");
    } catch (err) {
      flash("error", toError(err, "Enregistrement impossible."));
    }
  }

  async function savePreferences(next = preferences) {
    try {
      setPreferences(next);
      await updateUser({ preferences: next });
      flash("success", "Préférences enregistrées.");
    } catch (err) {
      flash("error", toError(err, "Enregistrement impossible."));
    }
  }

  async function changePassword() {
    try {
      await authApi.changePassword(passwords);
      setPasswords({ current_password: "", new_password: "", password_confirm: "" });
      flash("success", "Mot de passe modifié avec succès.");
    } catch (err) {
      flash("error", toError(err, "Modification impossible."));
    }
  }

  const activeTabCfg = TABS.find((t) => t.id === tab);
  const colors = TAB_COLORS[activeTabCfg?.color || "electric"];

  const initials = [user?.first_name, user?.last_name]
    .filter(Boolean)
    .map((n) => n[0].toUpperCase())
    .join("") || (user?.username?.[0]?.toUpperCase() ?? "?");

  return (
    <div className="space-y-6">
      {/* ── Toast ── */}
      {toast && (
        <div
          className={`flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm font-medium transition-all ${
            toast.type === "success"
              ? "border-green-200 bg-green-50 text-energy dark:border-green-500/20 dark:bg-green-500/10"
              : "border-red-200 bg-red-50 text-danger dark:border-red-500/20 dark:bg-red-500/10"
          }`}
        >
          <span
            className={`flex h-5 w-5 items-center justify-center rounded-full ${
              toast.type === "success" ? "bg-energy" : "bg-danger"
            }`}
          >
            <Check size={11} className="text-white" strokeWidth={3} />
          </span>
          {toast.msg}
        </div>
      )}

      {/* ── Profile hero card ── */}
      <div className="card overflow-hidden">
        {/* Top banner */}
        <div className="h-20 bg-gradient-to-r from-navy-panel via-navy to-electric" />
        <div className="flex flex-wrap items-end justify-between gap-4 px-6 pb-5">
          {/* Avatar */}
          <div className="-mt-10 flex items-end gap-4">
            <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-electric text-2xl font-bold text-white shadow-lg ring-4 ring-white dark:ring-navy-panel">
              {initials}
            </div>
            <div className="pb-1">
              <p className="text-lg font-bold text-navy dark:text-white">
                {user?.first_name && user?.last_name
                  ? `${user.first_name} ${user.last_name}`
                  : user?.username}
              </p>
              <p className="text-sm text-slate-500">{user?.email}</p>
            </div>
          </div>
          {/* Quick stats */}
          <div className="flex flex-wrap gap-3 pb-1">
            <StatChip label="Rôle" value={user?.role || "USER"} color="electric" />
            <StatChip
              label="Téléphone"
              value={user?.phone_verified ? "Vérifié" : "Non vérifié"}
              color={user?.phone_verified ? "energy" : "solar"}
            />
          </div>
        </div>
      </div>

      {/* ── Main layout ── */}
      <div className="grid gap-6 xl:grid-cols-[240px_1fr_280px]">

        {/* ── Sidebar tabs ── */}
        <nav className="card h-fit p-2">
          {TABS.map((t) => {
            const active = tab === t.id;
            const c = TAB_COLORS[t.color];
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition last:mb-0 ${
                  active
                    ? `${c.bg} ${c.text} ring-1 ${c.border}`
                    : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-white/5"
                }`}
              >
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                    active ? c.bg : "bg-slate-100 dark:bg-white/5"
                  }`}
                >
                  <t.icon
                    size={15}
                    className={active ? c.icon : "text-slate-400 dark:text-slate-500"}
                    strokeWidth={2.4}
                  />
                </span>
                <span className="flex-1 text-left">{t.label}</span>
                {active && (
                  <ChevronRight size={14} className={c.icon} strokeWidth={2.4} />
                )}
              </button>
            );
          })}
        </nav>

        {/* ── Content ── */}
        <div className="card p-6">
          {/* Section header */}
          {activeTabCfg && (
            <div className={`mb-6 flex items-center gap-3 rounded-xl border p-3 ${colors.bg} ${colors.border}`}>
              <span className={`flex h-9 w-9 items-center justify-center rounded-lg bg-white dark:bg-navy-panel shadow-sm`}>
                <activeTabCfg.icon size={18} className={colors.icon} strokeWidth={2.4} />
              </span>
              <div>
                <p className={`font-bold ${colors.text}`}>{activeTabCfg.label}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {TAB_SUBTITLES[activeTabCfg.id]}
                </p>
              </div>
            </div>
          )}

          {/* ─ Profil ─ */}
          {tab === "profile" && (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <FieldInput label="Prénom" icon={User} value={profile.first_name} onChange={(v) => setProfile((p) => ({ ...p, first_name: v }))} />
                <FieldInput label="Nom de famille" icon={User} value={profile.last_name} onChange={(v) => setProfile((p) => ({ ...p, last_name: v }))} />
                <FieldInput label="Adresse e-mail" icon={Mail} value={profile.email} onChange={(v) => setProfile((p) => ({ ...p, email: v }))} type="email" />
                <FieldInput label="Téléphone" icon={Phone} value={profile.phone} onChange={(v) => setProfile((p) => ({ ...p, phone: v }))} type="tel" />
              </div>
              <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 p-3 dark:border-white/5 dark:bg-white/5">
                <Badge value={user?.phone_verified ? "VALID" : "WARNING"}>
                  {user?.phone_verified ? "Téléphone vérifié" : "Non vérifié"}
                </Badge>
                <span className="text-xs text-slate-400">·</span>
                <span className="text-sm text-slate-500">Identifiant : <strong className="text-slate-700 dark:text-slate-200">{user?.username}</strong></span>
              </div>
              <div className="flex justify-end">
                <button className="btn-primary gap-2" onClick={saveProfile}>
                  <Check size={15} strokeWidth={2.8} /> Enregistrer le profil
                </button>
              </div>
            </div>
          )}

          {/* ─ Sécurité ─ */}
          {tab === "security" && (
            <div className="space-y-5">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Choisissez un mot de passe fort (min. 8 caractères, une lettre et un chiffre).
              </p>
              <div className="grid gap-4 sm:grid-cols-3">
                <PasswordInput label="Mot de passe actuel" value={passwords.current_password} onChange={(v) => setPasswords((p) => ({ ...p, current_password: v }))} />
                <PasswordInput label="Nouveau mot de passe" value={passwords.new_password} onChange={(v) => setPasswords((p) => ({ ...p, new_password: v }))} />
                <PasswordInput label="Confirmation" value={passwords.password_confirm} onChange={(v) => setPasswords((p) => ({ ...p, password_confirm: v }))} />
              </div>
              <StrengthBar password={passwords.new_password} />
              <div className="flex justify-end">
                <button className="btn-primary gap-2" style={{ background: "#DC2626" }} onClick={changePassword}>
                  <Lock size={15} strokeWidth={2.6} /> Modifier le mot de passe
                </button>
              </div>
            </div>
          )}

          {/* ─ Affichage ─ */}
          {tab === "display" && (
            <div className="space-y-6">
              <SegmentedField
                label="Thème de l'interface"
                hint="Choisissez entre clair, sombre ou automatique selon le système."
                value={theme}
                options={[["light", "Clair", Sun], ["dark", "Sombre", Moon], ["system", "Système", Monitor]]}
                onChange={setTheme}
              />
              <SegmentedField
                label="Langue"
                value={preferences.language}
                options={[["fr", "Français"]]}
                onChange={(language) => savePreferences({ ...preferences, language })}
              />
              <SegmentedField
                label="Unités de mesure"
                hint="Valeurs affichées dans les graphiques et tableaux."
                value={preferences.units}
                options={[["metric", "kW · kWh · V · A · °C"]]}
                onChange={(units) => savePreferences({ ...preferences, units })}
              />
            </div>
          )}

          {/* ─ Notifications ─ */}
          {tab === "notifications" && (
            <div className="space-y-3">
              <ToggleRow
                label="Alertes critiques"
                desc="Reçevez une notification pour chaque alerte de niveau CRITICAL."
                checked={preferences.notifications?.critical}
                onChange={(v) => {
                  const next = { ...preferences, notifications: { ...preferences.notifications, critical: v } };
                  setPreferences(next);
                }}
              />
              <ToggleRow
                label="Alertes système"
                desc="Notifications pour les événements système (batteries, réseau...)."
                checked={preferences.notifications?.system}
                onChange={(v) => {
                  const next = { ...preferences, notifications: { ...preferences.notifications, system: v } };
                  setPreferences(next);
                }}
              />
              <ToggleRow
                label="Rapports journaliers"
                desc="Recevez un résumé quotidien de l'activité du micro-réseau."
                checked={preferences.notifications?.reports}
                onChange={(v) => {
                  const next = { ...preferences, notifications: { ...preferences.notifications, reports: v } };
                  setPreferences(next);
                }}
              />
              <div className="flex justify-end pt-2">
                <button className="btn-primary gap-2" onClick={() => savePreferences(preferences)}>
                  <Check size={15} strokeWidth={2.8} /> Enregistrer
                </button>
              </div>
            </div>
          )}

          {/* ─ API ─ */}
          {tab === "api" && (
            <div className="space-y-3">
              {[
                { label: "Mode interface web", value: "Backend Django / DRF", icon: Server },
                { label: "URL de l'API", value: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api", icon: Zap },
                { label: "Application mobile", value: "Cloud · Edge · URL locale configurable", icon: Server },
              ].map((row) => (
                <div key={row.label} className="flex items-center gap-4 rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-white/5 dark:bg-white/5">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-navy/10 dark:bg-white/5">
                    <row.icon size={16} className="text-navy dark:text-slate-300" strokeWidth={2.2} />
                  </span>
                  <div>
                    <p className="text-xs text-slate-400">{row.label}</p>
                    <p className="break-all font-medium text-slate-700 dark:text-slate-200">{row.value}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ─ Confidentialité ─ */}
          {tab === "privacy" && (
            <div className="space-y-4">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Gérez l'exportation de vos données ou supprimez votre compte.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <ActionCard
                  icon={Shield}
                  title="Exporter les données"
                  desc="Téléchargez toutes vos mesures au format CSV."
                  color="energy"
                  onClick={() => window.open(reportsApi.exportCsvUrl(), "_blank")}
                  label="Télécharger CSV"
                />
                <ActionCard
                  icon={Shield}
                  title="Supprimer le compte"
                  desc="Action irréversible — toutes les données seront effacées."
                  color="danger"
                  disabled
                  label="Non disponible"
                />
              </div>
            </div>
          )}
        </div>

        {/* ── Right panel : résumé compte ── */}
        <div className="space-y-4">
          {/* Account summary */}
          <div className="card p-5">
            <p className="mb-4 text-sm font-bold uppercase tracking-wide text-slate-400">
              Résumé du compte
            </p>
            <div className="space-y-3">
              {[
                { label: "Identifiant",   value: user?.username,                    icon: User },
                { label: "E-mail",        value: user?.email,                        icon: Mail },
                { label: "Téléphone",     value: user?.phone || "Non renseigné",    icon: Phone },
                { label: "Rôle",          value: user?.role || "USER",              icon: KeyRound },
              ].map((row) => (
                <div key={row.label} className="flex items-center gap-3">
                  <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-slate-100 dark:bg-white/5">
                    <row.icon size={13} className="text-slate-400 dark:text-slate-500" strokeWidth={2.4} />
                  </span>
                  <div className="min-w-0">
                    <p className="text-[11px] text-slate-400">{row.label}</p>
                    <p className="truncate text-sm font-semibold text-slate-700 dark:text-slate-200">{row.value}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 border-t border-slate-100 pt-4 dark:border-white/5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Vérification tél.</span>
                <Badge value={user?.phone_verified ? "VALID" : "WARNING"}>
                  {user?.phone_verified ? "Vérifié" : "En attente"}
                </Badge>
              </div>
            </div>
          </div>

          {/* Navigation rapide */}
          <div className="card p-5">
            <p className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-400">
              Accès rapide
            </p>
            <div className="space-y-1">
              {TABS.map((t) => {
                const active = tab === t.id;
                const c = TAB_COLORS[t.color];
                return (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition ${
                      active
                        ? `${c.bg} ${c.text}`
                        : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-white/5"
                    }`}
                  >
                    <t.icon size={13} strokeWidth={2.4} />
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Sous-composants
───────────────────────────────────────────── */

const TAB_SUBTITLES = {
  profile:       "Informations personnelles et coordonnées",
  security:      "Modifier le mot de passe et la sécurité",
  display:       "Thème, langue et unités de mesure",
  notifications: "Configurer les alertes et rapports",
  api:           "Détails de connexion à l'API backend",
  privacy:       "Export des données et gestion du compte",
};

function FieldInput({ label, icon: Icon, value, onChange, type = "text" }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </span>
      <div className="relative">
        {Icon && (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
            <Icon size={15} strokeWidth={2.2} />
          </span>
        )}
        <input
          type={type}
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          className="input pl-9"
        />
      </div>
    </label>
  );
}

function PasswordInput({ label, value, onChange }) {
  const [show, setShow] = useState(false);
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </span>
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
          <Lock size={15} strokeWidth={2.2} />
        </span>
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete="new-password"
          className="input pl-9 pr-10"
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setShow((s) => !s)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-electric"
        >
          {show ? <EyeOff size={15} strokeWidth={2.2} /> : <Eye size={15} strokeWidth={2.2} />}
        </button>
      </div>
    </label>
  );
}

function StrengthBar({ password }) {
  const len = password.length;
  const hasLetter = /[A-Za-z]/.test(password);
  const hasDigit = /\d/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password);
  const score = (len >= 8 ? 1 : 0) + (hasLetter ? 1 : 0) + (hasDigit ? 1 : 0) + (hasSpecial ? 1 : 0);
  if (!password) return null;
  const labels = ["Très faible", "Faible", "Moyen", "Fort", "Très fort"];
  const colors = ["bg-danger", "bg-danger", "bg-solar", "bg-energy", "bg-energy"];
  return (
    <div className="space-y-1.5">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full transition-all ${
              i < score ? colors[score] : "bg-slate-200 dark:bg-white/10"
            }`}
          />
        ))}
      </div>
      <p className="text-xs text-slate-400">{labels[score]}</p>
    </div>
  );
}

function SegmentedField({ label, hint, value, options, onChange }) {
  return (
    <div>
      <p className="mb-0.5 text-sm font-semibold text-slate-700 dark:text-slate-200">{label}</p>
      {hint && <p className="mb-2 text-xs text-slate-400">{hint}</p>}
      <div className="flex flex-wrap gap-2">
        {options.map(([id, text, Icon]) => (
          <button
            key={id}
            type="button"
            onClick={() => onChange(id)}
            className={value === id ? "btn-primary" : "btn-ghost"}
          >
            {Icon && <Icon size={14} strokeWidth={2.4} />}
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

function ToggleRow({ label, desc, checked, onChange }) {
  return (
    <div
      className={`flex items-center justify-between gap-4 rounded-xl border p-4 transition ${
        checked
          ? "border-energy/30 bg-green-50 dark:border-energy/20 dark:bg-green-500/5"
          : "border-slate-100 dark:border-white/5"
      }`}
    >
      <div>
        <p className="font-semibold text-slate-700 dark:text-slate-200">{label}</p>
        <p className="text-xs text-slate-400">{desc}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-electric focus:ring-offset-2 ${
          checked ? "bg-energy" : "bg-slate-200 dark:bg-white/10"
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition-transform ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}

function ActionCard({ icon: Icon, title, desc, color, onClick, disabled, label }) {
  const c = TAB_COLORS[color] || TAB_COLORS.electric;
  return (
    <div className={`rounded-xl border p-4 ${c.bg} ${c.border}`}>
      <span className={`inline-flex h-9 w-9 items-center justify-center rounded-lg bg-white dark:bg-navy-panel shadow-sm mb-3`}>
        <Icon size={17} className={c.icon} strokeWidth={2.4} />
      </span>
      <p className={`font-semibold ${c.text}`}>{title}</p>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{desc}</p>
      <button
        className={`mt-4 btn text-xs px-3 py-1.5 ${disabled ? "btn-ghost opacity-50 cursor-not-allowed" : "btn-primary"}`}
        style={!disabled && color === "energy" ? { background: "#16A34A" } : {}}
        onClick={onClick}
        disabled={disabled}
      >
        {label}
      </button>
    </div>
  );
}

function StatChip({ label, value, color }) {
  const c = TAB_COLORS[color] || TAB_COLORS.electric;
  return (
    <div className={`rounded-xl border px-3 py-2 ${c.bg} ${c.border}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`text-sm font-bold ${c.text}`}>{value}</p>
    </div>
  );
}

function toError(err, fallback) {
  const data = err?.response?.data;
  if (!data) return fallback;
  return Object.values(data).flat().join(" ");
}
