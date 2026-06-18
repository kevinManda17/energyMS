import { useState } from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from "react-native";
import { HousePlug, MapPin } from "lucide-react-native";
import { Card } from "../components/Card";
import { Badge } from "../components/Badge";
import { FormInput } from "../components/FormInput";
import { Screen, PageTitle } from "../components/Screen";
import { housesApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

export default function HousesScreen() {
  const t = useTheme();
  const { houses, houseId, setHouseId, reload } = useActiveHouse();
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState("");

  async function createHouse() {
    if (!name.trim()) return;
    setError("");
    try {
      await housesApi.create({ name, location, status: "ONLINE" });
      setName("");
      setLocation("");
      await reload();
    } catch {
      setError("Creation impossible.");
    }
  }

  return (
    <Screen>
      <PageTitle title="Micro-reseaux" />
      <FlatList
        data={houses}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <TouchableOpacity onPress={() => setHouseId(item.id)}>
            <Card style={item.id === houseId ? { borderColor: palette.blue } : null}>
              <View style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.title, { color: t.text }]}>{item.name}</Text>
                  <Text style={{ color: t.sub }}>{item.location || "Localisation non renseignee"}</Text>
                  <Text style={{ color: t.sub, marginTop: 4 }}>
                    PV {item.pv_capacity_kw || 0} kW - Batterie {item.battery_capacity_kwh || 0} kWh
                  </Text>
                </View>
                <Badge value={item.status} />
              </View>
            </Card>
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={{ color: t.sub, textAlign: "center", marginTop: 30 }}>Aucun micro-reseau.</Text>}
        ListFooterComponent={
          <Card>
            <Text style={[styles.title, { color: t.text }]}>Nouveau micro-reseau</Text>
            <FormInput icon={HousePlug} value={name} onChangeText={setName} placeholder="ex: Residence Lubumbashi" />
            <FormInput icon={MapPin} value={location} onChangeText={setLocation} placeholder="ex: Lubumbashi, RDC" />
            {error ? <Text style={styles.error}>{error}</Text> : null}
            <TouchableOpacity style={styles.button} onPress={createHouse}>
              <Text style={styles.buttonText}>Ajouter</Text>
            </TouchableOpacity>
          </Card>
        }
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  title: { fontWeight: "700", marginBottom: 4 },
  button: { backgroundColor: palette.blue, padding: 12, borderRadius: 8, alignItems: "center", marginTop: 10 },
  buttonText: { color: "#fff", fontWeight: "700" },
  error: { color: palette.danger, marginTop: 8 },
});
