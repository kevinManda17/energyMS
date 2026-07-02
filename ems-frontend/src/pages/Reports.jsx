import { useQuery } from "@tanstack/react-query";
import { Bell, BatteryCharging, Download, Plug, Sun } from "lucide-react";
import { PageHeader, Loading } from "../components/ui";
import KpiCard from "../components/KpiCard";
import { reportsApi } from "../api/endpoints";
import { useHouseId } from "../hooks/useHouseId";
import { TOKEN_KEY } from "../api/client";
import { fmt } from "../utils/format";

const TABLE_ROWS = [
  {
    key:     "production",
    label:   "Production PV",
    icon:    Sun,
    valueColor: "text-energy font-semibold",
    bg:      "bg-green-50 dark:bg-green-500/5",
  },
  {
    key:     "consumption",
    label:   "Consommation",
    icon:    Plug,
    valueColor: "text-electric font-semibold",
    bg:      "bg-blue-50 dark:bg-blue-500/5",
  },
  {
    key:     "battery_soc",
    label:   "Batterie (SoC)",
    icon:    BatteryCharging,
    valueColor: "text-solar font-semibold",
    bg:      "",
  },
];

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
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
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
          <button className="btn-primary gap-2" onClick={exportCsv}>
            <Download size={16} /> Exporter CSV
          </button>
        }
      />

      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard icon={Sun}            tone="green" label="Production (jour)"    value={fmt(data?.production?.total)}  unit="kWh" hint={`moy. ${fmt(data?.production?.avg)} kW`}  />
        <KpiCard icon={Plug}           tone="blue"  label="Consommation (jour)"  value={fmt(data?.consumption?.total)} unit="kWh" hint={`moy. ${fmt(data?.consumption?.avg)} kW`} />
        <KpiCard icon={BatteryCharging}tone="amber" label="SoC batterie moyen"   value={fmt(data?.battery_soc?.avg, 0)} unit="%" />
        <KpiCard icon={Bell}           tone="red"   label="Alertes du jour"       value={data?.alerts_count ?? 0} hint={`${data?.decisions_count ?? 0} décision${data?.decisions_count !== 1 ? "s" : ""}`} />
      </div>

      {/* Tableau journalier */}
      <div className="card mt-6 overflow-hidden">
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <h3 className="font-semibold text-navy dark:text-white">
            Détail journalier
          </h3>
          {data?.date && (
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500 dark:bg-white/5">
              {data.date}
            </span>
          )}
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-500 dark:bg-white/5">
            <tr>
              <th className="px-5 py-3 font-medium">Indicateur</th>
              <th className="px-5 py-3 font-medium">Total</th>
              <th className="px-5 py-3 font-medium">Moyenne</th>
              <th className="px-5 py-3 font-medium">Min</th>
              <th className="px-5 py-3 font-medium">Max</th>
            </tr>
          </thead>
          <tbody>
            {TABLE_ROWS.map(({ key, label, icon: Icon, valueColor, bg }) => {
              const v = data?.[key];
              return (
                <tr key={key} className={`border-t border-slate-100 dark:border-white/5 ${bg}`}>
                  <td className="px-5 py-3">
                    <span className="flex items-center gap-2 font-medium">
                      <Icon size={14} className={valueColor.replace(" font-semibold", "")} strokeWidth={2.2} />
                      {label}
                    </span>
                  </td>
                  <td className={`px-5 py-3 ${valueColor}`}>{fmt(v?.total)}</td>
                  <td className={`px-5 py-3 ${valueColor}`}>{fmt(v?.avg)}</td>
                  <td className="px-5 py-3 text-slate-500">{fmt(v?.min)}</td>
                  <td className="px-5 py-3 text-slate-500">{fmt(v?.max)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
