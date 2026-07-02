import { ScrollView, Text, TouchableOpacity, StyleSheet, View } from "react-native";
import {
  Bell,
  ChartLine,
  ChevronRight,
  Cpu,
  FileText,
  Lock,
  Palette,
  Shield,
  User,
  Wifi,
} from "lucide-react-native";
import { Screen, PageTitle } from "../components/Screen";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

const TOOLS = [
  { label: "Equipements",  screen: "Devices",    icon: Cpu,      color: palette.blue   },
  { label: "Prévisions",   screen: "Forecasting", icon: ChartLine, color: palette.green  },
  { label: "Rapports",     screen: "Reports",    icon: FileText,  color: palette.solar  },
];

const ACCOUNT = [
  { label: "Profil",          screen: "Profile",       icon: User,    color: palette.blue    },
  { label: "Mot de passe",    screen: "Password",      icon: Lock,    color: "#7C3AED"       },
  { label: "Affichage",       screen: "Display",       icon: Palette, color: palette.solar   },
  { label: "Notifications",   screen: "Notifications", icon: Bell,    color: palette.green   },
  { label: "Réseau",          screen: "Network",       icon: Wifi,    color: palette.navy    },
  { label: "Confidentialité", screen: "Privacy",       icon: Shield,  color: palette.slate   },
];

export default function MoreScreen({ navigation }) {
  const t = useTheme();
  return (
    <Screen>
      <PageTitle title="Plus" />

      {/* Outils */}
      <SectionLabel label="Explorer" t={t} />
      {TOOLS.map((item) => (
        <NavRow key={item.screen} item={item} navigation={navigation} t={t} />
      ))}

      {/* Compte */}
      <SectionLabel label="Mon compte" t={t} />
      <View style={[styles.group, { backgroundColor: t.card, borderColor: t.border }]}>
        {ACCOUNT.map((item, i) => (
          <GroupRow
            key={item.screen}
            item={item}
            navigation={navigation}
            t={t}
            last={i === ACCOUNT.length - 1}
          />
        ))}
      </View>
    </Screen>
  );
}

function SectionLabel({ label, t }) {
  return (
    <Text style={[styles.sectionLabel, { color: t.sub }]}>{label.toUpperCase()}</Text>
  );
}

function NavRow({ item, navigation, t }) {
  const Icon = item.icon;
  return (
    <TouchableOpacity
      style={[styles.navRow, { borderColor: t.border, backgroundColor: t.card }]}
      onPress={() => navigation.navigate(item.screen)}
      activeOpacity={0.75}
    >
      <View style={[styles.iconWrap, { backgroundColor: item.color + "18" }]}>
        <Icon color={item.color} size={19} strokeWidth={2.2} />
      </View>
      <Text style={[styles.navLabel, { color: t.text }]}>{item.label}</Text>
      <ChevronRight color={t.sub} size={18} strokeWidth={2.4} />
    </TouchableOpacity>
  );
}

function GroupRow({ item, navigation, t, last }) {
  const Icon = item.icon;
  return (
    <TouchableOpacity
      style={[styles.groupRow, !last && { borderBottomWidth: 1, borderBottomColor: t.border }]}
      onPress={() => navigation.navigate(item.screen)}
      activeOpacity={0.75}
    >
      <View style={[styles.iconWrap, { backgroundColor: item.color + "18" }]}>
        <Icon color={item.color} size={18} strokeWidth={2.2} />
      </View>
      <Text style={[styles.navLabel, { color: t.text }]}>{item.label}</Text>
      <ChevronRight color={t.sub} size={17} strokeWidth={2.4} />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  sectionLabel: {
    fontSize: 11, fontWeight: "700", letterSpacing: 0.8,
    marginTop: 18, marginBottom: 6, marginHorizontal: 4,
  },
  navRow: {
    minHeight: 60, borderWidth: 1, borderRadius: 12,
    paddingHorizontal: 14, marginBottom: 8,
    flexDirection: "row", alignItems: "center", gap: 12,
  },
  group: { borderWidth: 1, borderRadius: 14, overflow: "hidden", marginBottom: 8 },
  groupRow: {
    minHeight: 56, paddingHorizontal: 14,
    flexDirection: "row", alignItems: "center", gap: 12,
  },
  iconWrap: {
    width: 36, height: 36, borderRadius: 10,
    alignItems: "center", justifyContent: "center",
  },
  navLabel: { flex: 1, fontSize: 15, fontWeight: "700" },
});
