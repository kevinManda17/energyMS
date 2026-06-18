import { useEffect, useState } from "react";
import { Bell, Eye, KeyRound, Lock, Server, Shield, User } from "lucide-react";
import { PageHeader, Badge } from "../components/ui";
import { authApi, reportsApi } from "../api/endpoints";
import { useAuthStore } from "../store/auth";
import { useUIStore } from "../store/ui";

const TABS = [
  ["profile", "Profil", User],
  ["security", "Securite", KeyRound],
  ["display", "Affichage", Eye],
  ["notifications", "Notifications", Bell],
  ["api", "API", Server],
  ["privacy", "Confidentialite", Shield],
];

const defaultPreferences = {
  language: "fr",
  units: "metric",
  notifications: {
    critical: true,
    system: true,
    reports: false,
  },
};

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore();
  const { theme, setTheme } = useUIStore();
  const [tab, setTab] = useState("profile");
  const [profile, setProfile] = useState({});
  const [preferences, setPreferences] = useState(defaultPreferences);
  const [passwords, setPasswords] = useState({
    current_password: "",
    new_password: "",
    password_confirm: "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setProfile({
      first_name: user?.first_name || "",
      last_name: user?.last_name || "",
      email: user?.email || "",
      phone: user?.phone || "",
    });
    setPreferences({ ...defaultPreferences, ...(user?.preferences || {}) });
  }, [user]);

  function setProfileField(key, value) {
    setProfile((current) => ({ ...current, [key]: value }));
  }

  function setNotification(key, value) {
    setPreferences((current) => ({
      ...current,
      notifications: { ...current.notifications, [key]: value },
    }));
  }

  async function saveProfile() {
    setMessage("");
    setError("");
    try {
      await updateUser({ ...profile, preferences });
      setMessage("Parametres enregistres.");
    } catch (err) {
      setError(toError(err, "Enregistrement impossible."));
    }
  }

  async function savePreferences(nextPreferences = preferences) {
    setMessage("");
    setError("");
    try {
      setPreferences(nextPreferences);
      await updateUser({ preferences: nextPreferences });
      setMessage("Preferences enregistrees.");
    } catch (err) {
      setError(toError(err, "Enregistrement impossible."));
    }
  }

  async function changePassword() {
    setMessage("");
    setError("");
    try {
      await authApi.changePassword(passwords);
      setPasswords({ current_password: "", new_password: "", password_confirm: "" });
      setMessage("Mot de passe modifie.");
    } catch (err) {
      setError(toError(err, "Modification impossible."));
    }
  }

  return (
    <>
      <PageHeader title="Parametres" subtitle="Profil, securite et preferences utilisateur." />

      <div className="mb-6 flex flex-wrap gap-2">
        {TABS.map(([id, label, Icon]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={tab === id ? "btn-primary" : "btn-ghost"}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="card p-6">
          {tab === "profile" && (
            <Section title="Profil utilisateur">
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Prenom" value={profile.first_name} onChange={(v) => setProfileField("first_name", v)} />
                <Input label="Nom" value={profile.last_name} onChange={(v) => setProfileField("last_name", v)} />
                <Input label="E-mail" value={profile.email} onChange={(v) => setProfileField("email", v)} />
                <Input label="Telephone" value={profile.phone} onChange={(v) => setProfileField("phone", v)} />
              </div>
              <div className="flex items-center gap-3">
                <Badge value={user?.phone_verified ? "VALID" : "WARNING"}>
                  {user?.phone_verified ? "Telephone verifie" : "Telephone non verifie"}
                </Badge>
                <span className="text-sm text-slate-500">Role: {user?.role}</span>
              </div>
              <button className="btn-primary w-fit" onClick={saveProfile}>Enregistrer</button>
            </Section>
          )}

          {tab === "security" && (
            <Section title="Securite">
              <div className="grid gap-4 sm:grid-cols-3">
                <Input label="Mot de passe actuel" type="password" value={passwords.current_password} onChange={(v) => setPasswords({ ...passwords, current_password: v })} />
                <Input label="Nouveau mot de passe" type="password" value={passwords.new_password} onChange={(v) => setPasswords({ ...passwords, new_password: v })} />
                <Input label="Confirmation" type="password" value={passwords.password_confirm} onChange={(v) => setPasswords({ ...passwords, password_confirm: v })} />
              </div>
              <button className="btn-primary w-fit" onClick={changePassword}>
                <Lock size={16} /> Modifier le mot de passe
              </button>
            </Section>
          )}

          {tab === "display" && (
            <Section title="Affichage et unites">
              <Segmented
                label="Theme"
                value={theme}
                options={[
                  ["light", "Clair"],
                  ["dark", "Sombre"],
                  ["system", "Systeme"],
                ]}
                onChange={setTheme}
              />
              <Segmented
                label="Langue"
                value={preferences.language}
                options={[["fr", "Francais"]]}
                onChange={(language) => savePreferences({ ...preferences, language })}
              />
              <Segmented
                label="Unites"
                value={preferences.units}
                options={[["metric", "kW, kWh, V, A, C"]]}
                onChange={(units) => savePreferences({ ...preferences, units })}
              />
            </Section>
          )}

          {tab === "notifications" && (
            <Section title="Notifications">
              <Toggle label="Alertes critiques" checked={preferences.notifications?.critical} onChange={(v) => setNotification("critical", v)} />
              <Toggle label="Alertes systeme" checked={preferences.notifications?.system} onChange={(v) => setNotification("system", v)} />
              <Toggle label="Rapports" checked={preferences.notifications?.reports} onChange={(v) => setNotification("reports", v)} />
              <button className="btn-primary w-fit" onClick={() => savePreferences(preferences)}>Enregistrer</button>
            </Section>
          )}

          {tab === "api" && (
            <Section title="Preferences API">
              <Info label="Mode web" value="Backend Django/DRF partage avec le mobile" />
              <Info label="Base API" value={import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"} />
              <Info label="Mobile" value="Cloud, edge ou URL locale depuis l'application mobile" />
            </Section>
          )}

          {tab === "privacy" && (
            <Section title="Confidentialite">
              <a className="btn-ghost w-fit" href={reportsApi.exportCsvUrl()}>
                Exporter les donnees CSV
              </a>
              <button className="btn-ghost w-fit opacity-60" disabled>
                Suppression de compte
              </button>
            </Section>
          )}
        </div>

        <div className="card h-fit p-5">
          <h3 className="font-semibold text-navy dark:text-white">Etat du compte</h3>
          <div className="mt-4 space-y-3 text-sm">
            <Info label="Utilisateur" value={user?.username} />
            <Info label="E-mail" value={user?.email} />
            <Info label="Telephone" value={user?.phone || "Non renseigne"} />
            <Info label="Verification" value={user?.phone_verified ? "Verifie" : "Non verifie"} />
          </div>
          {message && <p className="mt-4 text-sm text-energy">{message}</p>}
          {error && <p className="mt-4 text-sm text-danger">{error}</p>}
        </div>
      </div>
    </>
  );
}

function Section({ title, children }) {
  return (
    <div className="space-y-5">
      <h3 className="font-semibold text-navy dark:text-white">{title}</h3>
      {children}
    </div>
  );
}

function Input({ label, value, onChange, type = "text" }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium">{label}</span>
      <input className="input" type={type} value={value || ""} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function Info({ label, value }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="break-words font-medium">{value}</div>
    </div>
  );
}

function Segmented({ label, value, options, onChange }) {
  return (
    <div>
      <div className="mb-2 text-sm font-medium">{label}</div>
      <div className="flex flex-wrap gap-2">
        {options.map(([id, text]) => (
          <button
            key={id}
            type="button"
            onClick={() => onChange(id)}
            className={value === id ? "btn-primary" : "btn-ghost"}
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center justify-between rounded-xl border border-slate-100 p-3 dark:border-white/10">
      <span className="font-medium">{label}</span>
      <input type="checkbox" checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  );
}

function toError(err, fallback) {
  const data = err.response?.data;
  if (!data) return fallback;
  return Object.values(data).flat().join(" ");
}
