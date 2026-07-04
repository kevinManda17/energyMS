import { ScrollView, View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { Gauge, Languages, Monitor, Moon, Palette, Sun } from "lucide-react-native";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { useThemeStore } from "../store/theme";

const THEME_OPTIONS = [
  { id: "light",  label: "Clair",   icon: Sun     },
  { id: "dark",   label: "Sombre",  icon: Moon    },
  { id: "system", label: "Système", icon: Monitor },
];

export default function DisplayScreen() {
  const t = useTheme();
  const { theme: activeTheme, setTheme } = useThemeStore();

  return (
    <ScrollView
      style={{ backgroundColor: t.bg }}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      {/* Icon block */}
      <View style={[styles.iconBlock, { backgroundColor: palette.blue + "14" }]}>
        <Palette color={palette.blue} size={38} strokeWidth={1.8} />
      </View>

      {/* Thème */}
      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.cardTitle, { color: t.text }]}>Thème</Text>
        <Text style={[styles.cardSub, { color: t.sub }]}>Choisissez l'apparence de l'application.</Text>
        <View style={styles.themeGrid}>
          {THEME_OPTIONS.map(({ id, label, icon: Icon }) => {
            const active = activeTheme === id;
            return (
              <TouchableOpacity
                key={id}
                onPress={() => setTheme(id)}
                activeOpacity={0.8}
                style={[
                  styles.themeCard,
                  {
                    borderColor: active ? palette.blue : t.border,
                    backgroundColor: active ? palette.blue + "14" : t.bg,
                  },
                ]}
              >
                <Icon
                  color={active ? palette.blue : t.sub}
                  size={22}
                  strokeWidth={2.2}
                />
                <Text style={[styles.themeLabel, { color: active ? palette.blue : t.text }]}>
                  {label}
                </Text>
                {active && <View style={[styles.activeDot, { backgroundColor: palette.blue }]} />}
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* Langue & Unités */}
      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.cardTitle, { color: t.text }]}>Langue & Unités</Text>
        <InfoRow icon={Languages} label="Langue" value="Français" t={t} />
        <InfoRow icon={Gauge}     label="Unités" value="kW · kWh · V · A · °C" t={t} />
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

function InfoRow({ icon: Icon, label, value, t }) {
  return (
    <View style={[styles.infoRow, { borderBottomColor: t.border }]}>
      <View style={styles.infoLeft}>
        <Icon color={t.sub} size={15} strokeWidth={2.2} />
        <Text style={{ color: t.sub, fontSize: 13 }}>{label}</Text>
      </View>
      <Text style={{ color: t.text, fontSize: 13, fontWeight: "600" }}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { paddingBottom: 24 },

  iconBlock: {
    width: 80, height: 80, borderRadius: 24,
    alignItems: "center", justifyContent: "center",
    alignSelf: "center", marginTop: 24, marginBottom: 8,
  },
  toast: { margin: 14, marginBottom: 0, padding: 12, borderRadius: 10 },
  toastText: { color: "#fff", fontWeight: "700", textAlign: "center" },

  card: { marginHorizontal: 14, marginTop: 14, borderRadius: 14, borderWidth: 1, padding: 16 },
  cardTitle: { fontSize: 15, fontWeight: "800", marginBottom: 4 },
  cardSub: { fontSize: 13, lineHeight: 18, color: "#94A3B8", marginBottom: 14 },

  themeGrid: { flexDirection: "row", gap: 10, marginTop: 4 },
  themeCard: {
    flex: 1, borderWidth: 1.5, borderRadius: 12,
    paddingVertical: 14, alignItems: "center", gap: 6,
  },
  themeLabel: { fontSize: 12, fontWeight: "700" },
  activeDot: { width: 6, height: 6, borderRadius: 3 },

  infoRow: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    paddingVertical: 10, borderBottomWidth: 0.5,
  },
  infoLeft: { flexDirection: "row", alignItems: "center", gap: 8 },
});
