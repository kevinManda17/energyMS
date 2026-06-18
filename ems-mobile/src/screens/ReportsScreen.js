import { useCallback, useEffect, useState } from "react";
import { ScrollView, Text, TouchableOpacity, StyleSheet } from "react-native";
import { Card, KpiCard } from "../components/Card";
import { reportsApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt } from "../utils/format";

export default function ReportsScreen() {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [report, setReport] = useState(null);
  const [exportUrl, setExportUrl] = useState("");

  const load = useCallback(async () => {
    if (!houseId) return;
    const today = new Date().toISOString().slice(0, 10);
    const res = await reportsApi.daily({ house: houseId, date: today });
    setReport(res.data);
    setExportUrl(await reportsApi.exportCsvUrl());
  }, [houseId]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  return (
    <ScrollView style={{ backgroundColor: t.bg }} contentContainerStyle={{ padding: 12 }}>
      <Text style={[styles.h1, { color: t.text }]}>Rapports</Text>
      <Text style={[styles.sub, { color: t.sub }]}>{activeHouse?.name || "Aucun micro-reseau"}</Text>

      <Text style={[styles.section, { color: t.text }]}>Resume journalier</Text>
      <KpiCard label="Production totale" value={fmt(report?.production?.total)} unit="kWh" color={palette.green} />
      <KpiCard label="Consommation totale" value={fmt(report?.consumption?.total)} unit="kWh" color={palette.blue} />
      <KpiCard label="Decisions" value={report?.decisions_count ?? 0} color={palette.solar} />
      <KpiCard label="Alertes" value={report?.alerts_count ?? 0} color={palette.danger} />

      <Card>
        <Text style={[styles.title, { color: t.text }]}>Export CSV</Text>
        <Text style={{ color: t.sub, marginTop: 6 }}>{exportUrl || "Lien indisponible"}</Text>
        <TouchableOpacity style={styles.button} onPress={load}>
          <Text style={styles.buttonText}>Rafraichir</Text>
        </TouchableOpacity>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  h1: { fontSize: 24, fontWeight: "800", marginTop: 8 },
  sub: { marginTop: 4, marginBottom: 16 },
  section: { fontSize: 16, fontWeight: "800", marginTop: 12, marginBottom: 8 },
  title: { fontWeight: "700" },
  button: { backgroundColor: palette.blue, borderRadius: 8, padding: 12, alignItems: "center", marginTop: 12 },
  buttonText: { color: "#fff", fontWeight: "700" },
});
