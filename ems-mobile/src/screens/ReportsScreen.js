import { useCallback, useEffect, useRef, useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, RefreshControl } from "react-native";
import { Activity, BarChart2, Battery, HousePlug, Link, RefreshCw, Scale, Zap } from "lucide-react-native";
import { Card } from "../components/Card";
import LineChart from "../components/LineChart";
import { ScreenScroll, PageTitle } from "../components/Screen";
import { reportsApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt } from "../utils/format";

const PERIODS = [
  { label: "Aujourd'hui", days: 1 },
  { label: "7 jours", days: 7 },
  { label: "30 jours", days: 30 },
];

const AUTO_REFRESH_MS = 5 * 60 * 1000;

// Un bilan dont la valeur absolue est sous ce seuil est considéré à
// l'équilibre (bruit de mesure, arrondis d'intégration).
const BALANCE_EPSILON_KWH = 0.1;

function balanceState(balance) {
  if (balance > BALANCE_EPSILON_KWH) return { label: "Excédent", color: palette.green };
  if (balance < -BALANCE_EPSILON_KWH) return { label: "Déficit", color: palette.danger };
  return { label: "Équilibre", color: palette.slate };
}

function fmtDay(iso) {
  return iso
    ? new Date(`${iso}T00:00:00`).toLocaleDateString("fr-FR", {
        weekday: "short", day: "2-digit", month: "short",
      })
    : "—";
}

function fmtDayShort(iso) {
  return iso
    ? new Date(`${iso}T00:00:00`).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" })
    : "";
}

export default function ReportsScreen() {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [summary, setSummary] = useState(null);
  const [period, setPeriod] = useState(PERIODS[1]);
  const [exportUrl, setExportUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [fromCache, setFromCache] = useState(false);
  const [error, setError] = useState("");
  const loadRef = useRef(() => {});

  const load = useCallback(async (silent = false) => {
    if (!houseId) {
      setSummary(null);
      return;
    }
    if (!silent) setLoading(true);
    setError("");
    try {
      const res = await reportsApi.summary({ house: houseId, days: period.days });
      setSummary(res.data);
      setFromCache(!!res.fromCache);
      const url = await reportsApi.exportCsvUrl();
      setExportUrl(url);
    } catch {
      setError("Impossible de charger les rapports. Vérifiez la connexion.");
    } finally {
      if (!silent) setLoading(false);
    }
  }, [houseId, period]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  // Mise à jour automatique toutes les 5 minutes (silencieuse : pas de
  // spinner pour ne pas perturber la lecture).
  loadRef.current = load;
  useEffect(() => {
    const id = setInterval(() => loadRef.current(true), AUTO_REFRESH_MS);
    return () => clearInterval(id);
  }, []);

  async function onPullRefresh() {
    setRefreshing(true);
    await load(true);
    setRefreshing(false);
  }

  const today = summary?.today;
  const days = summary?.days || [];
  const hasData = (summary?.totals?.samples || 0) > 0;
  const todayBalance = balanceState(today?.balance_kwh || 0);

  /* ── Aucun micro-réseau sélectionné ── */
  if (!houseId) {
    return (
      <ScreenScroll>
        <PageTitle title="Rapports énergétiques" subtitle="Suivi de la production et de la consommation" />
        <View style={styles.emptyWrap}>
          <HousePlug color={t.sub} size={42} strokeWidth={1.5} />
          <Text style={[styles.emptyText, { color: t.sub }]}>
            Veuillez sélectionner un micro-réseau pour afficher les rapports.
          </Text>
        </View>
      </ScreenScroll>
    );
  }

  return (
    <ScreenScroll
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onPullRefresh} tintColor={palette.blue} />
      }
    >
      {/* En-tête + bouton Actualiser */}
      <View style={styles.headerRow}>
        <View style={{ flex: 1 }}>
          <PageTitle
            title="Rapports énergétiques"
            subtitle={activeHouse?.name || "Suivi de la production et de la consommation"}
          />
        </View>
        <TouchableOpacity
          style={[styles.refreshBtn, loading && styles.refreshBtnLoading]}
          onPress={() => load()}
          disabled={loading}
          activeOpacity={0.8}
          accessibilityLabel="Actualiser les rapports"
        >
          {loading ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <RefreshCw color="#fff" size={17} strokeWidth={2.4} />
          )}
        </TouchableOpacity>
      </View>

      {fromCache ? (
        <Text style={[styles.cacheNote, { color: t.sub }]}>Données en cache (hors-ligne)</Text>
      ) : null}

      {error ? (
        <View style={[styles.errorBox, { backgroundColor: palette.dangerLight, borderColor: "#FCA5A5" }]}>
          <Text style={{ color: palette.danger, fontSize: 13, fontWeight: "600" }}>{error}</Text>
        </View>
      ) : null}

      {/* Filtres de période */}
      <View style={styles.filterRow}>
        {PERIODS.map((p) => {
          const active = period.days === p.days;
          return (
            <TouchableOpacity
              key={p.days}
              onPress={() => setPeriod(p)}
              style={[
                styles.chip,
                {
                  borderColor: active ? palette.blue : t.border,
                  backgroundColor: active ? palette.blue : "transparent",
                },
              ]}
            >
              <Text style={{ color: active ? "#fff" : t.sub, fontSize: 12, fontWeight: "700" }}>
                {p.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Cartes résumé du jour */}
      <Text style={[styles.sectionLabel, { color: t.sub }]}>Résumé du jour</Text>
      <View style={styles.kpiGrid}>
        <KpiCard
          icon={Zap}
          label="Production du jour"
          value={fmt(today?.production_kwh)}
          unit="kWh"
          color={palette.green}
          bg={palette.greenLight}
          t={t}
        />
        <KpiCard
          icon={Activity}
          label="Consommation du jour"
          value={fmt(today?.consumption_kwh)}
          unit="kWh"
          color={palette.blue}
          bg={palette.blueLight}
          t={t}
        />
        <KpiCard
          icon={Scale}
          label="Bilan énergétique"
          value={fmt(today?.balance_kwh)}
          unit="kWh"
          color={todayBalance.color}
          bg={todayBalance.color + "18"}
          sub={todayBalance.label}
          t={t}
        />
        <KpiCard
          icon={Battery}
          label="Batterie moyenne"
          value={today?.battery_soc_avg != null ? fmt(today.battery_soc_avg, 0) : "—"}
          unit={today?.battery_soc_avg != null ? "%" : ""}
          color={palette.solar}
          bg={palette.solarLight}
          t={t}
        />
      </View>

      {/* Graphique production vs consommation */}
      {hasData && days.length > 1 && (
        <Card style={styles.chartCard}>
          <View style={styles.chartHeader}>
            <Text style={[styles.chartTitle, { color: t.text }]}>
              Production vs consommation ({period.label.toLowerCase()})
            </Text>
            <View style={styles.legend}>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: palette.green }]} />
                <Text style={[styles.legendLabel, { color: t.sub }]}>Production</Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: palette.blue }]} />
                <Text style={[styles.legendLabel, { color: t.sub }]}>Conso.</Text>
              </View>
            </View>
          </View>
          <LineChart
            series={[
              { data: days.map((d) => d.production_kwh), color: palette.green, label: "Production" },
              { data: days.map((d) => d.consumption_kwh), color: palette.blue, label: "Consommation" },
            ]}
            labels={days.map((d) => fmtDayShort(d.date))}
            height={170}
            unit="kWh"
            showDots={days.length <= 10}
          />
        </Card>
      )}

      {/* Historique journalier */}
      <Text style={[styles.sectionLabel, { color: t.sub }]}>Historique journalier</Text>
      {!hasData ? (
        <View style={styles.emptyWrap}>
          <BarChart2 color={t.sub} size={38} strokeWidth={1.5} />
          <Text style={[styles.emptyText, { color: t.sub }]}>
            Aucune donnée énergétique disponible pour cette période.
          </Text>
        </View>
      ) : (
        <View style={[styles.historyCard, { backgroundColor: t.card, borderColor: t.border }]}>
          <View style={[styles.historyHead, { borderBottomColor: t.border }]}>
            <Text style={[styles.headCell, styles.cellDate, { color: t.sub }]}>Date</Text>
            <Text style={[styles.headCell, styles.cellNum, { color: palette.green }]}>Prod.</Text>
            <Text style={[styles.headCell, styles.cellNum, { color: palette.blue }]}>Conso.</Text>
            <Text style={[styles.headCell, styles.cellNum, { color: t.sub }]}>Bilan</Text>
          </View>
          {[...days].reverse().map((d, i, arr) => {
            const st = balanceState(d.balance_kwh);
            const noData = d.samples === 0;
            return (
              <View
                key={d.date}
                style={[styles.historyRow, i < arr.length - 1 && { borderBottomWidth: 1, borderBottomColor: t.border }]}
              >
                <Text style={[styles.cellDate, { color: t.text, fontWeight: "600", fontSize: 12 }]}>
                  {fmtDay(d.date)}
                </Text>
                {noData ? (
                  <Text style={[styles.noDataCell, { color: t.sub }]}>aucune mesure</Text>
                ) : (
                  <>
                    <Text style={[styles.cellNum, { color: palette.green, fontWeight: "700", fontSize: 12 }]}>
                      {fmt(d.production_kwh)}
                    </Text>
                    <Text style={[styles.cellNum, { color: palette.blue, fontWeight: "700", fontSize: 12 }]}>
                      {fmt(d.consumption_kwh)}
                    </Text>
                    <Text style={[styles.cellNum, { color: st.color, fontWeight: "700", fontSize: 12 }]}>
                      {d.balance_kwh > 0 ? "+" : ""}{fmt(d.balance_kwh)}
                    </Text>
                  </>
                )}
              </View>
            );
          })}
          <Text style={[styles.tableUnit, { color: t.sub }]}>Valeurs en kWh</Text>
        </View>
      )}

      {/* Export CSV */}
      <View style={[styles.exportCard, { backgroundColor: t.card, borderColor: t.border }]}>
        <View style={styles.exportHeader}>
          <View style={[styles.exportIconWrap, { backgroundColor: palette.blueLight }]}>
            <Link color={palette.blue} size={18} strokeWidth={2.4} />
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

function KpiCard({ icon: Icon, label, value, unit, color, bg, sub, t }) {
  return (
    <View style={[styles.kpiCard, { backgroundColor: t.card, borderColor: t.border }]}>
      <View style={[styles.kpiIconWrap, { backgroundColor: bg }]}>
        <Icon color={color} size={18} strokeWidth={2.4} />
      </View>
      <Text style={[styles.kpiLabel, { color: t.sub }]}>{label}</Text>
      <Text style={[styles.kpiValue, { color }]}>
        {value}
        {unit ? <Text style={[styles.kpiUnit, { color: t.sub }]}> {unit}</Text> : null}
      </Text>
      {sub ? <Text style={[styles.kpiSub, { color }]}>{sub}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 10 },
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
  cacheNote: { fontSize: 12, fontWeight: "600", marginBottom: 8 },
  errorBox: { borderWidth: 1, borderRadius: 10, padding: 12, marginBottom: 10 },

  filterRow: { flexDirection: "row", gap: 8, marginBottom: 14 },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 7 },

  sectionLabel: {
    fontSize: 12, fontWeight: "700", textTransform: "uppercase",
    letterSpacing: 0.8, marginBottom: 10,
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
    width: 36, height: 36, borderRadius: 10,
    alignItems: "center", justifyContent: "center", marginBottom: 10,
  },
  kpiLabel: { fontSize: 12, lineHeight: 16, marginBottom: 6 },
  kpiValue: { fontSize: 22, fontWeight: "800" },
  kpiUnit: { fontSize: 12, fontWeight: "600" },
  kpiSub: { fontSize: 11, fontWeight: "700", marginTop: 3 },

  chartCard: { marginBottom: 16, paddingBottom: 4 },
  chartHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8, gap: 8 },
  chartTitle: { fontSize: 13, fontWeight: "700", flexShrink: 1 },
  legend: { flexDirection: "row", gap: 10 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 5 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendLabel: { fontSize: 11 },

  historyCard: { borderWidth: 1, borderRadius: 14, paddingHorizontal: 14, paddingTop: 4, marginBottom: 16 },
  historyHead: { flexDirection: "row", alignItems: "center", paddingVertical: 9, borderBottomWidth: 1, gap: 6 },
  headCell: { fontSize: 11, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.4 },
  historyRow: { flexDirection: "row", alignItems: "center", paddingVertical: 10, gap: 6 },
  cellDate: { flex: 1.4 },
  cellNum: { flex: 1, textAlign: "right" },
  noDataCell: { flex: 3, textAlign: "right", fontSize: 12, fontStyle: "italic" },
  tableUnit: { fontSize: 10, textAlign: "right", paddingVertical: 8 },

  emptyWrap: { alignItems: "center", marginTop: 24, marginBottom: 24, gap: 12, paddingHorizontal: 20 },
  emptyText: { textAlign: "center", fontSize: 14, lineHeight: 21 },

  exportCard: { borderWidth: 1, borderRadius: 14, padding: 16, marginBottom: 8 },
  exportHeader: { flexDirection: "row", alignItems: "center", gap: 12 },
  exportIconWrap: {
    width: 40, height: 40, borderRadius: 12,
    alignItems: "center", justifyContent: "center",
  },
  exportTitle: { fontWeight: "700", fontSize: 15, marginBottom: 3 },
  exportUrl: { fontSize: 11 },
});
