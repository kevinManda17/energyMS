import { useCallback, useEffect, useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";
import {
  Activity,
  CircuitBoard,
  Cpu,
  Plus,
  Radio,
  Settings2,
  Thermometer,
  Zap,
} from "lucide-react-native";
import { Badge } from "../components/Badge";
import { ScreenScroll, PageTitle } from "../components/Screen";
import { devicesApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt } from "../utils/format";

const SENSOR_ICONS = {
  voltage:      { icon: Zap,          color: palette.solar },
  current:      { icon: Activity,     color: palette.blue },
  temperature:  { icon: Thermometer,  color: palette.danger },
  production:   { icon: CircuitBoard, color: palette.green },
  consumption:  { icon: Cpu,          color: palette.blue },
  battery:      { icon: Radio,        color: palette.purple },
};

const EQUIP_ICONS = {
  SOLAR_PANEL:   { icon: CircuitBoard, color: palette.solar },
  BATTERY:       { icon: Radio,        color: palette.green },
  INVERTER:      { icon: Zap,          color: palette.blue },
  LOAD:          { icon: Cpu,          color: palette.slate },
  APPLIANCE:     { icon: Settings2,    color: palette.purple },
};

function getSensorMeta(sensor) {
  const key = Object.keys(SENSOR_ICONS).find((k) =>
    sensor.sensor_type?.toLowerCase().includes(k) || sensor.name?.toLowerCase().includes(k)
  );
  return SENSOR_ICONS[key] || { icon: Radio, color: palette.slate };
}

function getEquipMeta(item) {
  return EQUIP_ICONS[item.equipment_type] || { icon: Cpu, color: palette.slate };
}

export default function DevicesScreen() {
  const t = useTheme();
  const { houseId, activeHouse } = useActiveHouse();
  const [sensors, setSensors] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [form, setForm] = useState({ name: "", equipment_type: "", rated_power_kw: "" });
  const [showForm, setShowForm] = useState(false);

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
    setShowForm(false);
    load();
  }

  return (
    <ScreenScroll>
      <View style={styles.headerRow}>
        <PageTitle
          title="Équipements"
          subtitle={activeHouse?.name || "Aucun micro-réseau"}
        />
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => setShowForm((v) => !v)}
          activeOpacity={0.8}
        >
          <Plus color="#fff" size={18} strokeWidth={2.6} />
        </TouchableOpacity>
      </View>

      {/* Sensors section */}
      <View style={styles.sectionHeader}>
        <Radio color={palette.blue} size={16} strokeWidth={2.4} />
        <Text style={[styles.sectionTitle, { color: t.text }]}>Capteurs</Text>
        <View style={[styles.countBadge, { backgroundColor: palette.blueLight }]}>
          <Text style={{ color: palette.blue, fontSize: 11, fontWeight: "700" }}>{sensors.length}</Text>
        </View>
      </View>

      {sensors.length === 0 && (
        <Text style={[styles.empty, { color: t.sub }]}>Aucun capteur enregistré.</Text>
      )}
      {sensors.map((sensor) => {
        const meta = getSensorMeta(sensor);
        const IconComp = meta.icon;
        return (
          <View key={sensor.id} style={[styles.deviceCard, { backgroundColor: t.card, borderColor: t.border }]}>
            <View style={[styles.deviceIconWrap, { backgroundColor: meta.color + "15" }]}>
              <IconComp color={meta.color} size={18} strokeWidth={2.4} />
            </View>
            <View style={styles.deviceBody}>
              <Text style={[styles.deviceName, { color: t.text }]}>{sensor.name}</Text>
              <Text style={[styles.deviceSub, { color: t.sub }]}>
                {sensor.sensor_type}
                {sensor.unit ? ` · ${sensor.unit}` : ""}
              </Text>
            </View>
            <Badge value={sensor.is_active ? "ACTIVE" : "INACTIVE"} />
          </View>
        );
      })}

      {/* Equipment section */}
      <View style={[styles.sectionHeader, { marginTop: 18 }]}>
        <Cpu color={palette.purple} size={16} strokeWidth={2.4} />
        <Text style={[styles.sectionTitle, { color: t.text }]}>Charges & appareils</Text>
        <View style={[styles.countBadge, { backgroundColor: palette.purpleLight }]}>
          <Text style={{ color: palette.purple, fontSize: 11, fontWeight: "700" }}>{equipment.length}</Text>
        </View>
      </View>

      {equipment.length === 0 && (
        <Text style={[styles.empty, { color: t.sub }]}>Aucun équipement enregistré.</Text>
      )}
      {equipment.map((item) => {
        const meta = getEquipMeta(item);
        const IconComp = meta.icon;
        return (
          <View key={item.id} style={[styles.deviceCard, { backgroundColor: t.card, borderColor: t.border }]}>
            <View style={[styles.deviceIconWrap, { backgroundColor: meta.color + "15" }]}>
              <IconComp color={meta.color} size={18} strokeWidth={2.4} />
            </View>
            <View style={styles.deviceBody}>
              <Text style={[styles.deviceName, { color: t.text }]}>{item.name}</Text>
              <Text style={[styles.deviceSub, { color: t.sub }]}>
                {item.equipment_type || "Appareil"} · {fmt(item.rated_power_kw)} kW · {item.priority}
              </Text>
            </View>
            <Badge value={item.status} />
          </View>
        );
      })}

      {/* Add equipment form */}
      {showForm && (
        <View style={[styles.formCard, { backgroundColor: t.card, borderColor: palette.blue }]}>
          <Text style={[styles.formTitle, { color: t.text }]}>Nouvel équipement</Text>
          <FormField
            placeholder="Nom (ex: Réfrigérateur)"
            value={form.name}
            onChangeText={(v) => setForm({ ...form, name: v })}
            t={t}
          />
          <FormField
            placeholder="Type (LOAD, BATTERY, INVERTER...)"
            value={form.equipment_type}
            onChangeText={(v) => setForm({ ...form, equipment_type: v })}
            t={t}
          />
          <FormField
            placeholder="Puissance nominale (kW)"
            value={form.rated_power_kw}
            onChangeText={(v) => setForm({ ...form, rated_power_kw: v })}
            keyboardType="numeric"
            t={t}
          />
          <TouchableOpacity style={styles.saveBtn} onPress={createEquipment} activeOpacity={0.85}>
            <Plus color="#fff" size={16} strokeWidth={2.4} />
            <Text style={styles.saveBtnText}>Ajouter l'équipement</Text>
          </TouchableOpacity>
        </View>
      )}

      <View style={{ height: 20 }} />
    </ScreenScroll>
  );
}

function FormField({ placeholder, t, ...props }) {
  return (
    <TextInput
      style={[styles.formInput, { color: t.text, borderColor: t.border }]}
      placeholder={placeholder}
      placeholderTextColor={t.sub}
      {...props}
    />
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
  sectionHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  sectionTitle: { fontSize: 15, fontWeight: "800", flex: 1 },
  countBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999 },
  empty: { marginBottom: 10, fontSize: 13 },
  deviceCard: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    gap: 12,
  },
  deviceIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  deviceBody: { flex: 1 },
  deviceName: { fontWeight: "700", fontSize: 14, marginBottom: 3 },
  deviceSub: { fontSize: 12, lineHeight: 17 },
  formCard: {
    borderWidth: 1.5,
    borderRadius: 14,
    padding: 16,
    marginTop: 14,
  },
  formTitle: { fontSize: 15, fontWeight: "800", marginBottom: 12 },
  formInput: {
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
    fontSize: 14,
  },
  saveBtn: {
    backgroundColor: palette.blue,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    padding: 13,
    borderRadius: 10,
    marginTop: 4,
  },
  saveBtnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
});
