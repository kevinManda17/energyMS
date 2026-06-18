import { ScrollView, Text, View, StyleSheet } from "react-native";
import { Card } from "../components/Card";
import { Badge } from "../components/Badge";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

const PLANS = [
  {
    name: "Essentiel",
    price: "0 USD",
    badge: "INFO",
    items: ["1 micro-reseau", "Dashboard mobile", "Alertes de base"],
  },
  {
    name: "Pro",
    price: "19 USD/mois",
    badge: "ACTIVE",
    items: ["Micro-reseaux multiples", "Previsions horaires", "Rapports CSV"],
  },
  {
    name: "Entreprise",
    price: "Sur devis",
    badge: "WARNING",
    items: ["Support prioritaire", "Integrations avancees", "Deploiement dedie"],
  },
];

export default function PricingScreen() {
  const t = useTheme();
  return (
    <ScrollView style={{ backgroundColor: t.bg }} contentContainerStyle={{ padding: 12 }}>
      <Text style={[styles.h1, { color: t.text }]}>Tarifs</Text>
      <Text style={[styles.sub, { color: t.sub }]}>Plans accessibles depuis l'espace connecte.</Text>
      {PLANS.map((plan) => (
        <Card key={plan.name}>
          <View style={styles.row}>
            <View>
              <Text style={[styles.title, { color: t.text }]}>{plan.name}</Text>
              <Text style={{ color: palette.blue, fontWeight: "800", fontSize: 20 }}>{plan.price}</Text>
            </View>
            <Badge value={plan.badge} />
          </View>
          {plan.items.map((item) => (
            <Text key={item} style={{ color: t.sub, marginTop: 8 }}>
              {item}
            </Text>
          ))}
        </Card>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  h1: { fontSize: 24, fontWeight: "800", marginTop: 8 },
  sub: { marginTop: 4, marginBottom: 16 },
  row: { flexDirection: "row", justifyContent: "space-between", gap: 12 },
  title: { fontWeight: "800", fontSize: 17, marginBottom: 4 },
});
