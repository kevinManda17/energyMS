import { useCallback, useEffect, useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { AlertTriangle, BarChart2, FileText, Link, RefreshCw, Zap } from "lucide-react-native";
import { ScreenScroll, PageTitle } from "../components/Screen";
import { reportsApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt } from "../utils/format";

const today = () => new Date().toISOString().slice(0, 10);

export default function ReportsScreen() {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [report, setReport] = useState(null);
  const [exportUrl, setExportUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!houseId) return;
    setLoading(true);
    try {
      const res = await reportsApi.daily({ house: houseId, date: today() });
      setReport(res.data);
      const url = await reportsApi.exportCsvUrl();
      setExportUrl(url);
    } catch {
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [houseId]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  const kpis = [
    {
      label: "Production totale",
      value: fmt(report?.production?.total),
      unit: "kWh",
      color: palette.green,
      bg: palette.greenLight,
      icon: Zap,
    },
    {
      label: "Consommation totale",
      value: fmt(report?.consumption?.total),
      unit: "kWh",
      color: palette.blue,
      bg: palette.blueLight,
      icon: BarChart2,
    },
    {
      label: "Décisions prises",
      value: String(report?.decisions_count ?? "—"),
      unit: "",
      color: palette.purple,
      bg: palette.purpleLight,
      icon: FileText,
    },
    {
      label: "Alertes générées",
      value: String(report?.alerts_count ?? "—"),
      unit: "",
      color: palette.danger,
      bg: palette.dangerLight,
      icon: AlertTriangle,
    },
  ];

  return (
    <ScreenScroll>
      <View style={styles.headerRow}>
        <PageTitle
          title="Rapports"
          subtitle={activeHouse?.name || "Aucun micro-réseau"}
        />
        <TouchableOpacity
          style={[styles.refreshBtn, loading && styles.refreshBtnLoading]}
          onPress={load}
          disabled={loading}
          activeOpacity={0.8}
        >
          <RefreshCw color="#fff" size={17} strokeWidth={2.4} />
        </TouchableOpacity>
      </View>

      {/* Date badge */}
      <View style={[styles.dateBadge, { backgroundColor: t.card, borderColor: t.border }]}>
        <FileText color={palette.blue} size={14} strokeWidth={2.4} />
        <Text style={{ color: t.sub, fontSize: 13 }}>
          Résumé journalier du{" "}
          <Text style={{ color: t.text, fontWeight: "700" }}>
            {new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}
          </Text>
        </Text>
      </View>

      {/* KPI grid */}
      <View style={styles.kpiGrid}>
        {kpis.map((kpi) => {
          const IconComp = kpi.icon;
          return (
            <View key={kpi.label} style={[styles.kpiCard, { backgroundColor: t.card, borderColor: t.border }]}>
              <View style={[styles.kpiIconWrap, { backgroundColor: kpi.bg }]}>
                <IconComp color={kpi.color} size={18} strokeWidth={2.4} />
              </View>
              <Text style={[styles.kpiLabel, { color: t.sub }]}>{kpi.label}</Text>
              <Text style={[styles.kpiValue, { color: kpi.color }]}>
                {kpi.value}
                {kpi.unit ? <Text style={[styles.kpiUnit, { color: t.sub }]}> {kpi.unit}</Text> : null}
              </Text>
            </View>
          );
        })}
      </View>

      {/* Production breakdown */}
      {report?.production && (
        <View style={[styles.breakdownCard, { backgroundColor: t.card, borderColor: t.border }]}>
          <Text style={[styles.breakdownTitle, { color: t.text }]}>Détail production</Text>
          <BreakdownRow label="Maximum" value={fmt(report.production.max)} unit="kW" color={palette.green} t={t} />
          <BreakdownRow label="Minimum" value={fmt(report.production.min)} unit="kW" color={palette.green} t={t} />
          <BreakdownRow label="Moyenne" value={fmt(report.production.avg)} unit="kW" color={palette.green} t={t} isLast />
        </View>
      )}

      {report?.consumption && (
        <View style={[styles.breakdownCard, { backgroundColor: t.card, borderColor: t.border }]}>
          <Text style={[styles.breakdownTitle, { color: t.text }]}>Détail consommation</Text>
          <BreakdownRow label="Maximum" value={fmt(report.consumption.max)} unit="kW" color={palette.blue} t={t} />
          <BreakdownRow label="Minimum" value={fmt(report.consumption.min)} unit="kW" color={palette.blue} t={t} />
          <BreakdownRow label="Moyenne" value={fmt(report.consumption.avg)} unit="kW" color={palette.blue} t={t} isLast />
        </View>
      )}

      {/* Export */}
      <View style={[styles.exportCard, { backgroundColor: t.card, borderColor: t.border }]}>
        <View style={styles.exportHeader}>
          <View style={[styles.exportIconWrap, { backgroundColor: palette.greenLight }]}>
            <Link color={palette.green} size={18} strokeWidth={2.4} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={[styles.exportTitle, { color: t.text }]}>Export CSV</Text>
            <Text style={[styles.exportUrl, { color: t.sub }]} numberOfLines={1}>
              {exportUrl || "Lien indisponible"}
            </Text>
          </View>
        </View>
      </View>
    </ScreenScroll>
  );
}

function BreakdownRow({ label, value, unit, color, t, isLast }) {
  return (
    <View style={[styles.breakdownRow, !isLast && { borderBottomWidth: 1, borderBottomColor: t.border }]}>
      <Text style={{ color: t.sub, fontSize: 13 }}>{label}</Text>
      <Text style={{ color, fontWeight: "700", fontSize: 14 }}>
        {value} <Text style={{ color: t.sub, fontSize: 11 }}>{unit}</Text>
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  refreshBtn: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: palette.blue,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
  },
  refreshBtnLoading: { opacity: 0.6 },
  dateBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 16,
  },
  kpiGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 16 },
  kpiCard: {
    flex: 1,
    minWidth: "47%",
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
  },
  kpiIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 10,
  },
  kpiLabel: { fontSize: 12, lineHeight: 16, marginBottom: 6 },
  kpiValue: { fontSize: 22, fontWeight: "800" },
  kpiUnit: { fontSize: 12, fontWeight: "600" },
  breakdownCard: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
  },
  breakdownTitle: { fontSize: 14, fontWeight: "800", marginBottom: 10 },
  breakdownRow: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 10 },
  exportCard: { borderWidth: 1, borderRadius: 14, padding: 16, marginBottom: 8 },
  exportHeader: { flexDirection: "row", alignItems: "center", gap: 12 },
  exportIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  exportTitle: { fontWeight: "700", fontSize: 15, marginBottom: 3 },
  exportUrl: { fontSize: 11 },
});
