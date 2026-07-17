import { ScrollView, View, Text, TouchableOpacity, Linking, StyleSheet } from "react-native";
import { Download, FileText, Shield, Trash2 } from "lucide-react-native";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

const ITEMS = [
  {
    icon: Download,
    color: palette.blue,
    title: "Exporter mes données",
    desc: "Exportez l'historique de mesures et rapports depuis l'écran Rapports.",
    action: null,
    actionLabel: null,
  },
  {
    icon: FileText,
    color: palette.slate,
    title: "Politique de confidentialité",
    desc: "Consultez notre politique de traitement des données personnelles.",
    action: null,
    actionLabel: "Lire la politique",
  },
  {
    icon: Shield,
    color: palette.slate,
    title: "Données collectées",
    desc: "Mesures IoT, décisions du système expert, alertes, profil utilisateur.",
    action: null,
    actionLabel: null,
  },
  {
    icon: Trash2,
    color: palette.danger,
    title: "Suppression du compte",
    desc: "La suppression de compte n'est pas disponible en libre-service. Contactez l'administrateur.",
    action: null,
    actionLabel: null,
  },
];

export default function PrivacyScreen() {
  const t = useTheme();

  return (
    <ScrollView
      style={{ backgroundColor: t.bg }}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      {/* Icon block */}
      <View style={[styles.iconBlock, { backgroundColor: palette.slate + "22" }]}>
        <Shield color={palette.slate} size={38} strokeWidth={1.8} />
      </View>

      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.cardTitle, { color: t.text }]}>Confidentialité & données</Text>

        {ITEMS.map(({ icon: Icon, color, title, desc, action, actionLabel }, i) => (
          <View
            key={i}
            style={[styles.item, i < ITEMS.length - 1 && { borderBottomWidth: 1, borderBottomColor: t.border }]}
          >
            <View style={[styles.itemIcon, { backgroundColor: color + "18" }]}>
              <Icon color={color} size={17} strokeWidth={2.4} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.itemTitle, { color: t.text }]}>{title}</Text>
              <Text style={[styles.itemDesc, { color: t.sub }]}>{desc}</Text>
              {actionLabel && action ? (
                <TouchableOpacity onPress={() => Linking.openURL(action)} style={styles.itemLink}>
                  <Text style={{ color: palette.blue, fontSize: 13, fontWeight: "700" }}>
                    {actionLabel}
                  </Text>
                </TouchableOpacity>
              ) : null}
            </View>
          </View>
        ))}
      </View>

      <View style={[styles.versionCard, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.versionLabel, { color: t.sub }]}>Version de l'application</Text>
        <Text style={[styles.versionValue, { color: t.text }]}>EMS Mobile v1.0.0</Text>
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { paddingBottom: 24 },
  iconBlock: {
    width: 80, height: 80, borderRadius: 24,
    alignItems: "center", justifyContent: "center",
    alignSelf: "center", marginTop: 24, marginBottom: 8,
  },
  card: { marginHorizontal: 14, marginTop: 14, borderRadius: 14, borderWidth: 1, padding: 16 },
  cardTitle: { fontSize: 15, fontWeight: "800", marginBottom: 14 },

  item: { flexDirection: "row", gap: 12, paddingVertical: 14 },
  itemIcon: { width: 36, height: 36, borderRadius: 10, alignItems: "center", justifyContent: "center", marginTop: 2 },
  itemTitle: { fontSize: 14, fontWeight: "700", marginBottom: 3 },
  itemDesc: { fontSize: 12, lineHeight: 17 },
  itemLink: { marginTop: 6 },

  versionCard: {
    marginHorizontal: 14, marginTop: 14, borderRadius: 14, borderWidth: 1,
    padding: 16, alignItems: "center",
  },
  versionLabel: { fontSize: 12, marginBottom: 4 },
  versionValue: { fontSize: 14, fontWeight: "700" },
});
