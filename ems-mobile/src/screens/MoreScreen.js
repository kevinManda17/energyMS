import { Text, TouchableOpacity, StyleSheet, View } from "react-native";
import { ChartLine, ChevronRight, Cpu, FileText, Settings } from "lucide-react-native";
import { Screen, PageTitle } from "../components/Screen";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

const LINKS = [
  { label: "Equipements", screen: "Devices", icon: Cpu },
  { label: "Previsions", screen: "Forecasting", icon: ChartLine },
  { label: "Rapports", screen: "Reports", icon: FileText },
  { label: "Parametres", screen: "Settings", icon: Settings },
];

export default function MoreScreen({ navigation }) {
  const t = useTheme();
  return (
    <Screen>
      <PageTitle title="Plus" />
      {LINKS.map(({ label, screen, icon: Icon }) => (
        <TouchableOpacity
          key={screen}
          style={[styles.row, { borderColor: t.border, backgroundColor: t.card }]}
          onPress={() => navigation.navigate(screen)}
        >
          <View style={styles.left}>
            <View style={styles.iconWrap}>
              <Icon color={palette.blue} size={20} strokeWidth={2.4} />
            </View>
            <Text style={{ color: t.text, fontWeight: "800" }}>{label}</Text>
          </View>
          <ChevronRight color={t.sub} size={22} strokeWidth={2.4} />
        </TouchableOpacity>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: {
    minHeight: 64,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 14,
    marginBottom: 10,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  left: { flexDirection: "row", alignItems: "center", gap: 12 },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: palette.blue + "14",
    alignItems: "center",
    justifyContent: "center",
  },
});
