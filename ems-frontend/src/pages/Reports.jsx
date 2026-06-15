import { useQuery } from "@tanstack/react-query";
import { Download, Sun, Plug, BatteryCharging, Bell } from "lucide-react";
import { PageHeader, Loading } from "../components/ui";
import KpiCard from "../components/KpiCard";
import { reportsApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";
import { TOKEN_KEY } from "../api/client";
import { fmt } from "../utils/format";

export default function Reports() {
  const houseId = useHouseId();

  const { data, isLoading } = useQuery({
    queryKey: ["report-daily", houseId],
    queryFn: () => reportsApi.daily({ house: houseId }),
    enabled: !!houseId,
  });

  async function exportCsv() {
    const res = await fetch(reportsApi.exportCsvUrl(), {
      headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ems_measurements.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (isLoading) return <Loading />;

  return (
    <>
      <PageHeader
        title="Rapports"
        subtitle="Résumé journalier et analyse des performances énergétiques."
        actions={
          <button className="btn-primary" onClick={exportCsv}>
            <Download size={16} /> Exporter CSV
          </button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard icon={Sun} tone="green" label="Production (jour)" value={fmt(data?.production?.total)} unit="kWh" hint={`moy. ${fmt(data?.production?.avg)} kW`} />
        <KpiCard icon={Plug} tone="blue" label="Consommation (jour)" value={fmt(data?.consumption?.total)} unit="kWh" hint={`moy. ${fmt(data?.consumption?.avg)} kW`} />
        <KpiCard icon={BatteryCharging} tone="amber" label="SoC batterie moyen" value={fmt(data?.battery_soc?.avg, 0)} unit="%" />
        <KpiCard icon={Bell} tone="red" label="Alertes du jour" value={data?.alerts_count ?? 0} hint={`${data?.decisions_count ?? 0} décisions`} />
      </div>

      <div className="card mt-6 p-5">
        <h3 className="mb-3 font-semibold text-navy dark:text-white">Détail journalier — {data?.date}</h3>
        <table className="w-full text-sm">
          <thead className="text-left text-slate-400">
            <tr>
              <th className="pb-2">Indicateur</th>
              <th className="pb-2">Total</th>
              <th className="pb-2">Moyenne</th>
              <th className="pb-2">Min</th>
              <th className="pb-2">Max</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Production", data?.production],
              ["Consommation", data?.consumption],
              ["Batterie (SoC)", data?.battery_soc],
            ].map(([label, v]) => (
              <tr key={label} className="border-t border-slate-100 dark:border-white/5">
                <td className="py-2 font-medium">{label}</td>
                <td className="py-2">{fmt(v?.total)}</td>
                <td className="py-2">{fmt(v?.avg)}</td>
                <td className="py-2">{fmt(v?.min)}</td>
                <td className="py-2">{fmt(v?.max)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
