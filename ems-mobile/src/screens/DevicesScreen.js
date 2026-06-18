import { useCallback, useEffect, useState } from "react";
import { ScrollView, View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";
import { Card } from "../components/Card";
import { Badge } from "../components/Badge";
import { devicesApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt } from "../utils/format";

export default function DevicesScreen() {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [sensors, setSensors] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [form, setForm] = useState({ name: "", equipment_type: "", rated_power_kw: "" });

  const load = useCallback(async () => {
    if (!houseId) return;
    const [sensorRes, equipmentRes] = await Promise.all([
      devicesApi.sensors(houseId),
      devicesApi.equipment(houseId),
    ]);
    setSensors(sensorRes.data?.results || sensorRes.data || []);
    setEquipment(equipmentRes.data?.results || equipmentRes.data || []);
  }, [houseId]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  async function createEquipment() {
    if (!houseId || !form.name.trim()) return;
    await devicesApi.createEquipment(houseId, {
      name: form.name,
      equipment_type: form.equipment_type,
      rated_power_kw: Number(form.rated_power_kw || 0),
      priority: "NORMAL",
      status: "ACTIVE",
    });
    setForm({ name: "", equipment_type: "", rated_power_kw: "" });
    load();
  }

  return (
    <ScrollView style={{ backgroundColor: t.bg }} contentContainerStyle={{ padding: 12 }}>
      <Text style={[styles.h1, { color: t.text }]}>Equipements</Text>
      <Text style={[styles.sub, { color: t.sub }]}>{activeHouse?.name || "Aucun micro-reseau"}</Text>

      <Text style={[styles.section, { color: t.text }]}>Capteurs</Text>
      {sensors.length === 0 ? <Text style={{ color: t.sub }}>Aucun capteur.</Text> : null}
      {sensors.map((sensor) => (
        <Card key={sensor.id}>
          <View style={styles.row}>
            <View>
              <Text style={[styles.title, { color: t.text }]}>{sensor.name}</Text>
              <Text style={{ color: t.sub }}>{sensor.sensor_type} - {sensor.unit}</Text>
            </View>
            <Badge value={sensor.is_active ? "ACTIVE" : "INACTIVE"} />
          </View>
        </Card>
      ))}

      <Text style={[styles.section, { color: t.text }]}>Charges et appareils</Text>
      {equipment.length === 0 ? <Text style={{ color: t.sub }}>Aucun equipement.</Text> : null}
      {equipment.map((item) => (
        <Card key={item.id}>
          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.title, { color: t.text }]}>{item.name}</Text>
              <Text style={{ color: t.sub }}>
                {item.equipment_type || "Equipement"} - {fmt(item.rated_power_kw)} kW
              </Text>
              <Text style={{ color: t.sub }}>Priorite {item.priority}</Text>
            </View>
            <Badge value={item.status} />
          </View>
        </Card>
      ))}

      <Card>
        <Text style={[styles.title, { color: t.text }]}>Ajouter un equipement</Text>
        <TextInput style={[styles.input, { color: t.text, borderColor: t.border }]} value={form.name} onChangeText={(v) => setForm({ ...form, name: v })} placeholder="Nom" placeholderTextColor={t.sub} />
        <TextInput style={[styles.input, { color: t.text, borderColor: t.border }]} value={form.equipment_type} onChangeText={(v) => setForm({ ...form, equipment_type: v })} placeholder="Type" placeholderTextColor={t.sub} />
        <TextInput style={[styles.input, { color: t.text, borderColor: t.border }]} value={form.rated_power_kw} onChangeText={(v) => setForm({ ...form, rated_power_kw: v })} placeholder="Puissance kW" keyboardType="numeric" placeholderTextColor={t.sub} />
        <TouchableOpacity style={styles.button} onPress={createEquipment}>
          <Text style={styles.buttonText}>Ajouter</Text>
        </TouchableOpacity>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  h1: { fontSize: 24, fontWeight: "800", marginTop: 8 },
  sub: { marginTop: 4, marginBottom: 16 },
  section: { fontSize: 16, fontWeight: "800", marginTop: 12, marginBottom: 8 },
  row: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 12 },
  title: { fontWeight: "700", marginBottom: 4 },
  input: { borderWidth: 1, borderRadius: 8, padding: 10, marginTop: 10 },
  button: { backgroundColor: palette.blue, padding: 12, borderRadius: 8, alignItems: "center", marginTop: 10 },
  buttonText: { color: "#fff", fontWeight: "700" },
});
