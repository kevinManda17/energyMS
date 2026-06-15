import { useQuery } from "@tanstack/react-query";
import { Cpu, Plug } from "lucide-react";
import { PageHeader, Loading, Badge, Empty } from "../components/ui";
import { devicesApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";
import { fmt } from "../utils/format";

const PRIORITY_LABEL = {
  CRITICAL: "Critique",
  IMPORTANT: "Important",
  NORMAL: "Normal",
  NON_CRITICAL: "Non critique",
};

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
  if (isLoading) return <Loading />;

  const sensorList = sensors?.results || sensors || [];
  const equipList = equipment?.results || equipment || [];

  return (
    <>
      <PageHeader title="Équipements" subtitle="Capteurs et charges du micro-réseau." />

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <h3 className="mb-4 flex items-center gap-2 font-semibold text-navy dark:text-white">
            <Cpu size={18} /> Capteurs ({sensorList.length})
          </h3>
          <table className="w-full text-sm">
            <thead className="text-left text-slate-400">
              <tr>
                <th className="pb-2">Nom</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">Unité</th>
                <th className="pb-2">Statut</th>
              </tr>
            </thead>
            <tbody>
              {sensorList.map((s) => (
                <tr key={s.id} className="border-t border-slate-100 dark:border-white/5">
                  <td className="py-2 font-medium">{s.name}</td>
                  <td className="py-2 text-slate-500">{s.sensor_type}</td>
                  <td className="py-2 text-slate-500">{s.unit}</td>
                  <td className="py-2">
                    <Badge value={s.is_active ? "ACTIVE" : "INACTIVE"}>
                      {s.is_active ? "Actif" : "Inactif"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card p-5">
          <h3 className="mb-4 flex items-center gap-2 font-semibold text-navy dark:text-white">
            <Plug size={18} /> Charges / Équipements ({equipList.length})
          </h3>
          <table className="w-full text-sm">
            <thead className="text-left text-slate-400">
              <tr>
                <th className="pb-2">Nom</th>
                <th className="pb-2">Puissance</th>
                <th className="pb-2">Priorité</th>
                <th className="pb-2">Statut</th>
              </tr>
            </thead>
            <tbody>
              {equipList.map((e) => (
                <tr key={e.id} className="border-t border-slate-100 dark:border-white/5">
                  <td className="py-2 font-medium">{e.name}</td>
                  <td className="py-2 text-slate-500">{fmt(e.rated_power_kw, 2)} kW</td>
                  <td className="py-2 text-slate-500">{PRIORITY_LABEL[e.priority]}</td>
                  <td className="py-2">
                    <Badge value={e.status}>{e.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
