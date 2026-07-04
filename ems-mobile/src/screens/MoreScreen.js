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
  { label: "Equipements",  screen: "Devices",     icon: Cpu      },
  { label: "Prévisions",   screen: "Forecasting", icon: ChartLine },
  { label: "Rapports",     screen: "Reports",     icon: FileText  },
];

const ACCOUNT = [
  { label: "Profil",          screen: "Profile",       icon: User    },
  { label: "Mot de passe",    screen: "Password",      icon: Lock    },
  { label: "Affichage",       screen: "Display",       icon: Palette },
  { label: "Notifications",   screen: "Notifications", icon: Bell    },
  { label: "Réseau",          screen: "Network",       icon: Wifi    },
  { label: "Confidentialité", screen: "Privacy",       icon: Shield  },
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
      <View style={[styles.iconWrap, { backgroundColor: palette.blueLight }]}>
        <Icon color={palette.blue} size={19} strokeWidth={2.2} />
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
      <View style={[styles.iconWrap, { backgroundColor: palette.blueLight }]}>
        <Icon color={palette.blue} size={18} strokeWidth={2.2} />
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
