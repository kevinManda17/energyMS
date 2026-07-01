import { useState } from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from "react-native";
import { Battery, CheckCircle2, HousePlug, MapPin, Plus, Wifi, Zap } from "lucide-react-native";
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
  const [showForm, setShowForm] = useState(false);

  async function createHouse() {
    if (!name.trim()) return;
    setError("");
    try {
      await housesApi.create({ name, location, status: "ONLINE" });
      setName("");
      setLocation("");
      setShowForm(false);
      await reload();
    } catch {
      setError("Création impossible. Vérifiez la connexion.");
    }
  }

  return (
    <Screen>
      <View style={styles.headerRow}>
        <PageTitle title="Micro-réseaux" subtitle={`${houses.length} réseau${houses.length !== 1 ? "x" : ""}`} />
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => setShowForm((v) => !v)}
          activeOpacity={0.8}
        >
          <Plus color="#fff" size={18} strokeWidth={2.6} />
        </TouchableOpacity>
      </View>

      <FlatList
        data={houses}
        keyExtractor={(item) => String(item.id)}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={styles.emptyWrap}>
            <HousePlug color={t.sub} size={40} strokeWidth={1.5} />
            <Text style={[styles.emptyText, { color: t.sub }]}>
              Aucun micro-réseau.{"\n"}Ajoutez-en un ci-dessous.
            </Text>
          </View>
        }
        renderItem={({ item }) => {
          const isActive = item.id === houseId;
          return (
            <TouchableOpacity onPress={() => setHouseId(item.id)} activeOpacity={0.75}>
              <View
                style={[
                  styles.houseCard,
                  {
                    backgroundColor: t.card,
                    borderColor: isActive ? palette.blue : t.border,
                    borderWidth: isActive ? 2 : 1,
                  },
                ]}
              >
                {/* Status strip */}
                <View style={[styles.statusStrip, { backgroundColor: item.status === "ONLINE" ? palette.green : palette.slate }]} />

                <View style={styles.houseContent}>
                  <View style={styles.houseTop}>
                    <View style={[styles.houseIconWrap, { backgroundColor: isActive ? palette.blueLight : t.muted || "#F1F5F9" }]}>
                      <HousePlug color={isActive ? palette.blue : t.sub} size={20} strokeWidth={2.2} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.houseName, { color: t.text }]}>{item.name}</Text>
                      {item.location ? (
                        <View style={styles.locationRow}>
                          <MapPin color={t.sub} size={12} strokeWidth={2} />
                          <Text style={[styles.locationText, { color: t.sub }]}>{item.location}</Text>
                        </View>
                      ) : null}
                    </View>
                    {isActive ? (
                      <CheckCircle2 color={palette.blue} size={22} strokeWidth={2.4} />
                    ) : (
                      <Badge value={item.status} />
                    )}
                  </View>

                  {/* Capacity row */}
                  <View style={[styles.capacityRow, { borderTopColor: t.border }]}>
                    <CapacityItem icon={Zap} label="PV" value={`${item.pv_capacity_kw || 0} kW`} color={palette.solar} />
                    <View style={[styles.capacitySep, { backgroundColor: t.border }]} />
                    <CapacityItem icon={Battery} label="Batterie" value={`${item.battery_capacity_kwh || 0} kWh`} color={palette.green} />
                    <View style={[styles.capacitySep, { backgroundColor: t.border }]} />
                    <CapacityItem icon={Wifi} label="Statut" value={item.status || "—"} color={item.status === "ONLINE" ? palette.green : palette.slate} />
                  </View>
                </View>
              </View>
            </TouchableOpacity>
          );
        }}
        ListFooterComponent={
          showForm ? (
            <View style={[styles.formCard, { backgroundColor: t.card, borderColor: palette.blue }]}>
              <Text style={[styles.formTitle, { color: t.text }]}>Nouveau micro-réseau</Text>
              <FormInput
                icon={HousePlug}
                value={name}
                onChangeText={setName}
                placeholder="Nom (ex: Résidence Lubumbashi)"
                label="Nom du réseau"
              />
              <FormInput
                icon={MapPin}
                value={location}
                onChangeText={setLocation}
                placeholder="Localisation (ex: Lubumbashi, RDC)"
                label="Localisation"
              />
              {error ? <Text style={styles.formError}>{error}</Text> : null}
              <TouchableOpacity style={styles.saveBtn} onPress={createHouse} activeOpacity={0.85}>
                <HousePlug color="#fff" size={16} strokeWidth={2.4} />
                <Text style={styles.saveBtnText}>Créer le micro-réseau</Text>
              </TouchableOpacity>
            </View>
          ) : null
        }
      />
    </Screen>
  );
}

function CapacityItem({ icon: Icon, label, value, color }) {
  return (
    <View style={styles.capacityItem}>
      <Icon color={color} size={13} strokeWidth={2.4} />
      <Text style={{ color, fontSize: 11, fontWeight: "700" }}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  addBtn: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: palette.blue,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
  },
  emptyWrap: { alignItems: "center", marginTop: 60, gap: 14 },
  emptyText: { textAlign: "center", fontSize: 15, lineHeight: 22 },
  houseCard: {
    borderRadius: 14,
    marginBottom: 12,
    overflow: "hidden",
    flexDirection: "row",
  },
  statusStrip: { width: 5 },
  houseContent: { flex: 1, padding: 14 },
  houseTop: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 12 },
  houseIconWrap: {
    width: 42,
    height: 42,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  houseName: { fontSize: 16, fontWeight: "800", marginBottom: 3 },
  locationRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  locationText: { fontSize: 12 },
  capacityRow: {
    flexDirection: "row",
    alignItems: "center",
    borderTopWidth: 1,
    paddingTop: 10,
    gap: 8,
  },
  capacityItem: { flex: 1, alignItems: "center", flexDirection: "row", gap: 5, justifyContent: "center" },
  capacitySep: { width: 1, height: 20 },
  formCard: {
    borderWidth: 1.5,
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
  },
  formTitle: { fontSize: 15, fontWeight: "800", marginBottom: 4 },
  formError: { color: palette.danger, marginTop: 8, fontWeight: "600" },
  saveBtn: {
    backgroundColor: palette.blue,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    padding: 13,
    borderRadius: 10,
    marginTop: 12,
  },
  saveBtnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
});
