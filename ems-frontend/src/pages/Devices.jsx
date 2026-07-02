import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Battery,
  Cpu,
  Lightbulb,
  Plug,
  Sun,
  Thermometer,
  Wind,
  Zap,
} from "lucide-react";
import { PageHeader, Loading, Empty } from "../components/ui";
import { devicesApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";
import { fmt } from "../utils/format";

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
