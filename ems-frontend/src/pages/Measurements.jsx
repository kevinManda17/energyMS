import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, Loading, Empty } from "../components/ui";
import { ProdConsoChart } from "../components/EnergyChart";
import { measurementsApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";
import { fmt, fmtDate, fmtTime } from "../utils/format";

const TYPES = [
  ["", "Tous les types"],
  ["production", "Production"],
  ["consumption", "Consommation"],
  ["battery_soc", "Batterie (SoC)"],
  ["voltage", "Tension"],
];

function buildSeries(rows) {
  const acc = {};
  rows.forEach((m) => {
    const label = fmtTime(m.timestamp);
    acc[label] = acc[label] || { label };
    if (m.measurement_type === "production") acc[label].production = m.value;
    if (m.measurement_type === "consumption") acc[label].consumption = m.value;
  });
  return Object.values(acc).reverse();
}

export default function Measurements() {
  const houseId = useHouseId();
  const [type, setType] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["measurements", houseId, type],
    queryFn: () =>
      measurementsApi.history({
        house: houseId,
        measurement_type: type || undefined,
        ordering: "-timestamp",
        page_size: 100,
      }),
    enabled: !!houseId,
  });

  if (!houseId) return <Empty message="Sélectionnez un micro-réseau." />;
  if (isLoading) return <Loading />;

  const rows = data?.results || [];

  return (
    <>
      <PageHeader
        title="Mesures IoT"
        subtitle="Données collectées depuis les capteurs via MQTT."
        actions={
          <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
            {TYPES.map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        }
      />

      <div className="card mb-6 p-5">
        <h3 className="mb-4 font-semibold text-navy dark:text-white">Historique</h3>
        <ProdConsoChart data={buildSeries(rows)} />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-500 dark:bg-white/5">
            <tr>
              <th className="px-4 py-3">Horodatage</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Valeur</th>
              <th className="px-4 py-3">Unité</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.id} className="border-t border-slate-100 dark:border-white/5">
                <td className="px-4 py-2.5">{fmtDate(m.timestamp)}</td>
                <td className="px-4 py-2.5 text-slate-500">{m.measurement_type}</td>
                <td className="px-4 py-2.5 font-medium">{fmt(m.value)}</td>
                <td className="px-4 py-2.5 text-slate-500">{m.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <Empty message="Aucune mesure." />}
      </div>
    </>
  );
}
