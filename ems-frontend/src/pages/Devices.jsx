import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Battery,
  Cpu,
  Lightbulb,
  Plug,
  Power,
  PowerOff,
  Sun,
  Thermometer,
  Wind,
  Zap,
} from "lucide-react";
import { PageHeader, Loading, Empty } from "../components/ui";
import { devicesApi, relaysApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";
import { fmt } from "../utils/format";

/* Les trois lignes commutables du prototype (relais pilotés par l'ESP32). */
const RELAY_LINES = [
  { key: "line1", label: "Ligne 1", desc: "Lampe 10 W + prise 1" },
  { key: "line2", label: "Ligne 2", desc: "Lampe 20 W" },
  { key: "line3", label: "Ligne 3", desc: "Lampe 10 W + prise 2" },
];

/* ── Icônes et couleurs par type ── */
const SENSOR_ICON = {
  power_meter:  { icon: Zap,         color: "text-electric",  bg: "bg-blue-50 dark:bg-blue-500/10"   },
  battery:      { icon: Battery,     color: "text-solar",     bg: "bg-amber-50 dark:bg-amber-500/10" },
  solar_pv:     { icon: Sun,         color: "text-energy",    bg: "bg-green-50 dark:bg-green-500/10" },
  pv:           { icon: Sun,         color: "text-energy",    bg: "bg-green-50 dark:bg-green-500/10" },
  temperature:  { icon: Thermometer, color: "text-solar",     bg: "bg-amber-50 dark:bg-amber-500/10" },
  current:      { icon: Activity,    color: "text-electric",  bg: "bg-blue-50 dark:bg-blue-500/10"   },
  voltage:      { icon: Zap,         color: "text-electric",  bg: "bg-blue-50 dark:bg-blue-500/10"   },
};

const EQUIP_ICON = {
  lighting:   { icon: Lightbulb, color: "text-solar",    bg: "bg-amber-50 dark:bg-amber-500/10" },
  hvac:       { icon: Wind,      color: "text-electric", bg: "bg-blue-50 dark:bg-blue-500/10"   },
  appliance:  { icon: Plug,      color: "text-energy",   bg: "bg-green-50 dark:bg-green-500/10" },
};

const PRIORITY_COLOR = {
  CRITICAL:     "text-danger",
  IMPORTANT:    "text-solar",
  NORMAL:       "text-energy",
  NON_CRITICAL: "text-slate-400",
};
const PRIORITY_LABEL = {
  CRITICAL:     "Critique",
  IMPORTANT:    "Important",
  NORMAL:       "Normal",
  NON_CRITICAL: "Non critique",
};

function sensorMeta(type) {
  return SENSOR_ICON[type?.toLowerCase()] || { icon: Cpu,  color: "text-slate-500", bg: "bg-slate-100 dark:bg-white/5" };
}
function equipMeta(type) {
  return EQUIP_ICON[type?.toLowerCase()]  || { icon: Plug, color: "text-slate-500", bg: "bg-slate-100 dark:bg-white/5" };
}

export default function Devices() {
  const houseId = useHouseId();

  const { data: sensors, isLoading } = useQuery({
    queryKey: ["sensors", houseId],
    queryFn: () => devicesApi.sensors(houseId),
    enabled: !!houseId,
  });
  const { data: equipment } = useQuery({
    queryKey: ["equipment", houseId],
    queryFn: () => devicesApi.equipment(houseId),
    enabled: !!houseId,
  });

  if (!houseId) return <Empty message="Sélectionnez un micro-réseau." />;
  if (isLoading)  return <Loading />;

  const sensorList = sensors?.results  || sensors  || [];
  const equipList  = equipment?.results || equipment || [];

  return (
    <>
      <PageHeader title="Équipements" subtitle="Capteurs et charges du micro-réseau." />

      {/* Contrôle des lignes (relais ESP32) */}
      <RelayControl houseId={houseId} />

      {/* Capteurs */}
      <Section
        title="Capteurs IoT"
        icon={Cpu}
        count={sensorList.length}
        empty="Aucun capteur enregistré."
        isEmpty={sensorList.length === 0}
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sensorList.map((s) => {
            const m = sensorMeta(s.sensor_type);
            return (
              <SensorCard key={s.id} meta={m} name={s.name} type={s.sensor_type} unit={s.unit} active={s.is_active} />
            );
          })}
        </div>
      </Section>

      {/* Équipements */}
      <Section
        title="Charges / Équipements"
        icon={Plug}
        count={equipList.length}
        empty="Aucun équipement enregistré."
        isEmpty={equipList.length === 0}
        className="mt-6"
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {equipList.map((e) => {
            const m = equipMeta(e.equipment_type);
            return (
              <EquipCard
                key={e.id}
                meta={m}
                name={e.name}
                power={e.rated_power_kw}
                priority={e.priority}
                status={e.status}
              />
            );
          })}
        </div>
      </Section>
    </>
  );
}

/* ── Contrôle des lignes (relais) ── */

function contactLabel(iso) {
  if (!iso) return "Jamais contacté";
  const diffMs = Date.now() - new Date(iso).getTime();
  const online = diffMs < 15000; // ~5 sondages ratés à 3 s
  const mins = Math.round(diffMs / 60000);
  if (online) return "En ligne";
  if (mins < 60) return `Vu il y a ${Math.max(1, mins)} min`;
  return `Vu le ${new Date(iso).toLocaleString("fr-FR")}`;
}

function RelayControl({ houseId }) {
  const qc = useQueryClient();
  const [toast, setToast] = useState(null); // { type, msg }

  const { data: state, isLoading } = useQuery({
    queryKey: ["relays", houseId],
    queryFn: () => relaysApi.get(houseId),
    enabled: !!houseId,
    refetchInterval: 5000, // reflète le dernier contact du nœud
  });

  const mutation = useMutation({
    mutationFn: (patch) => relaysApi.set(houseId, patch),
    onSuccess: (data) => {
      qc.setQueryData(["relays", houseId], data);
      setToast({ type: "success", msg: "Commande envoyée au micro-réseau." });
      setTimeout(() => setToast(null), 3000);
    },
    onError: () => {
      setToast({ type: "error", msg: "Échec de l'envoi de la commande." });
      setTimeout(() => setToast(null), 3500);
    },
  });

  if (!houseId) return null;

  const online = state?.last_contact_at
    ? Date.now() - new Date(state.last_contact_at).getTime() < 15000
    : false;
  const allOn = state ? RELAY_LINES.every((l) => state[l.key]) : false;

  return (
    <div className="card mb-6 p-5">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 dark:bg-white/5">
          <Power size={15} className="text-electric" strokeWidth={2.2} />
        </span>
        <h3 className="font-semibold text-navy dark:text-white">Contrôle des lignes</h3>
        <span
          className={`badge ml-2 ${
            online
              ? "bg-green-50 text-energy dark:bg-green-500/10"
              : "bg-slate-100 text-slate-500 dark:bg-white/5"
          }`}
        >
          <span className={`mr-1 inline-block h-2 w-2 rounded-full ${online ? "bg-energy" : "bg-slate-400"}`} />
          {contactLabel(state?.last_contact_at)}
        </span>
        {/* Bouton unique : eteint tout si tout est allume, sinon allume tout. */}
        <button
          onClick={() =>
            mutation.mutate({ line1: !allOn, line2: !allOn, line3: !allOn })
          }
          disabled={isLoading || mutation.isPending || !state}
          className={`ml-auto inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${
            allOn
              ? "border-danger/30 text-danger hover:bg-red-50 dark:hover:bg-red-500/10"
              : "border-energy/30 text-energy hover:bg-green-50 dark:hover:bg-green-500/10"
          }`}
        >
          {allOn ? (
            <>
              <PowerOff size={15} strokeWidth={2.2} /> Tout éteindre
            </>
          ) : (
            <>
              <Power size={15} strokeWidth={2.2} /> Tout allumer
            </>
          )}
        </button>
      </div>

      {isLoading ? (
        <Loading label="Lecture de l'état des lignes…" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-3">
          {RELAY_LINES.map((line) => {
            const on = !!state?.[line.key];
            return (
              <div
                key={line.key}
                className="flex items-start gap-3 rounded-xl border border-slate-100 p-4 dark:border-white/5"
              >
                <span
                  className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${
                    on ? "bg-amber-50 dark:bg-amber-500/10" : "bg-slate-100 dark:bg-white/5"
                  }`}
                >
                  <Lightbulb
                    size={18}
                    className={on ? "text-solar" : "text-slate-400"}
                    strokeWidth={2.2}
                  />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-navy dark:text-white">{line.label}</p>
                  <p className="text-xs text-slate-400">{line.desc}</p>
                  <p className={`mt-0.5 text-xs font-semibold ${on ? "text-energy" : "text-slate-400"}`}>
                    {on ? "Connectée" : "Déconnectée"}
                  </p>
                </div>
                <Toggle
                  on={on}
                  disabled={mutation.isPending}
                  onChange={(next) => mutation.mutate({ [line.key]: next })}
                />
              </div>
            );
          })}
        </div>
      )}

      <p className="mt-4 text-xs text-slate-400">
        Ordre appliqué par le nœud ESP32 au prochain relevé (~3 s). Le nœud se
        lie automatiquement à ce micro-réseau dès que vous actionnez une ligne
        — aucun jeton à configurer dans le firmware.
      </p>

      {toast && (
        <div
          className={`mt-3 rounded-lg px-3 py-2 text-sm font-medium text-white ${
            toast.type === "success" ? "bg-energy" : "bg-danger"
          }`}
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}

function Toggle({ on, disabled, onChange }) {
  return (
    <button
      role="switch"
      aria-checked={on}
      disabled={disabled}
      onClick={() => onChange(!on)}
      className={`relative mt-0.5 h-6 w-11 flex-shrink-0 rounded-full transition disabled:opacity-50 ${
        on ? "bg-energy" : "bg-slate-300 dark:bg-white/20"
      }`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${
          on ? "left-[22px]" : "left-0.5"
        }`}
      />
    </button>
  );
}

/* ── Sous-composants ── */

function Section({ title, icon: Icon, count, empty, isEmpty, children, className = "" }) {
  return (
    <div className={`card p-5 ${className}`}>
      <h3 className="mb-4 flex items-center gap-2 font-semibold text-navy dark:text-white">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 dark:bg-white/5">
          <Icon size={15} className="text-slate-500" strokeWidth={2.2} />
        </span>
        {title}
        <span className="ml-auto text-xs font-normal text-slate-400">{count} élément{count !== 1 ? "s" : ""}</span>
      </h3>
      {isEmpty ? <Empty message={empty} /> : children}
    </div>
  );
}

function SensorCard({ meta, name, type, unit, active }) {
  const { icon: Icon, color, bg } = meta;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-slate-100 p-4 dark:border-white/5">
      <span className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${bg}`}>
        <Icon size={18} className={color} strokeWidth={2.2} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold text-navy dark:text-white">{name}</p>
        <p className="text-xs text-slate-400">{type}{unit ? ` · ${unit}` : ""}</p>
      </div>
      <StatusDot active={active} />
    </div>
  );
}

function EquipCard({ meta, name, power, priority, status }) {
  const { icon: Icon, color, bg } = meta;
  const priorityColor = PRIORITY_COLOR[priority] || "text-slate-400";
  const active = status === "ON" || status === "ACTIVE" || status === "ONLINE";
  return (
    <div className="flex items-start gap-3 rounded-xl border border-slate-100 p-4 dark:border-white/5">
      <span className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${bg}`}>
        <Icon size={18} className={color} strokeWidth={2.2} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold text-navy dark:text-white">{name}</p>
        <p className="text-xs text-slate-400">{fmt(power, 2)} kW</p>
        <p className={`text-xs font-semibold ${priorityColor}`}>{PRIORITY_LABEL[priority] || priority}</p>
      </div>
      <StatusDot active={active} label={status} />
    </div>
  );
}

function StatusDot({ active, label }) {
  return (
    <div className="flex flex-col items-center gap-1 pt-0.5">
      <span className={`h-2.5 w-2.5 rounded-full ${active ? "bg-energy" : "bg-slate-300 dark:bg-white/20"}`} />
      {label && <span className="text-[10px] text-slate-400">{label}</span>}
    </div>
  );
}
