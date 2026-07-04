import { useCallback, useEffect, useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, Modal, KeyboardAvoidingView, Platform, Pressable,
} from "react-native";
import {
  Activity,
  CircuitBoard,
  Cpu,
  Plus,
  Radio,
  Settings2,
  Thermometer,
  X,
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
  voltage:      { icon: Zap,          color: palette.slate },
  current:      { icon: Activity,     color: palette.slate },
  temperature:  { icon: Thermometer,  color: palette.slate },
  production:   { icon: CircuitBoard, color: palette.green },
  consumption:  { icon: Cpu,          color: palette.blue },
  battery:      { icon: Radio,        color: palette.solar },
};

const EQUIP_ICONS = {
  SOLAR_PANEL: { icon: CircuitBoard, color: palette.green },
  BATTERY:     { icon: Radio,        color: palette.solar },
  INVERTER:    { icon: Zap,          color: palette.blue },
  LOAD:        { icon: Cpu,          color: palette.slate },
  APPLIANCE:   { icon: Settings2,    color: palette.slate },
};

const EQUIP_TYPES = ["LOAD", "SOLAR_PANEL", "BATTERY", "INVERTER", "APPLIANCE"];

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
  const [sensors, setSensors]     = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm]           = useState({ name: "", equipment_type: "LOAD", rated_power_kw: "" });
  const [saving, setSaving]       = useState(false);

  const load = useCallback(async () => {
    if (!houseId) return;
    const [sensorRes, equipmentRes] = await Promise.all([
      devicesApi.sensors(houseId),
      devicesApi.equipment(houseId),
    ]);
    setSensors(sensorRes.data?.results   || sensorRes.data   || []);
    setEquipment(equipmentRes.data?.results || equipmentRes.data || []);
  }, [houseId]);

  useEffect(() => { load().catch(() => {}); }, [load]);

  async function createEquipment() {
    if (!houseId || !form.name.trim()) return;
    setSaving(true);
    try {
      await devicesApi.createEquipment(houseId, {
        name:             form.name,
        equipment_type:   form.equipment_type,
        rated_power_kw:   Number(form.rated_power_kw || 0),
        priority: "NORMAL",
        status:   "ACTIVE",
      });
      setForm({ name: "", equipment_type: "LOAD", rated_power_kw: "" });
      setShowModal(false);
      load();
    } catch {
      /* error silently — can add toast later */
    } finally {
      setSaving(false);
    }
  }

  return (
    <ScreenScroll>
      {/* Header */}
      <View style={styles.headerRow}>
        <PageTitle title="Équipements" subtitle={activeHouse?.name || "Aucun micro-réseau"} />
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => setShowModal(true)}
          activeOpacity={0.8}
        >
          <Plus color="#fff" size={18} strokeWidth={2.6} />
        </TouchableOpacity>
      </View>

      {/* Capteurs */}
      <SectionHeader icon={Radio} color={palette.blue} label="Capteurs" count={sensors.length} t={t} />
      {sensors.length === 0 && <EmptyText text="Aucun capteur enregistré." t={t} />}
      {sensors.map((sensor) => {
        const meta = getSensorMeta(sensor);
        return (
          <DeviceCard key={sensor.id} icon={meta.icon} color={meta.color} t={t}>
            <Text style={[styles.deviceName, { color: t.text }]}>{sensor.name}</Text>
            <Text style={[styles.deviceSub, { color: t.sub }]}>
              {sensor.sensor_type}{sensor.unit ? ` · ${sensor.unit}` : ""}
            </Text>
          </DeviceCard>
        );
      })}

      {/* Équipements */}
      <SectionHeader icon={Cpu} color={palette.slate} label="Charges & appareils" count={equipment.length} t={t} />
      {equipment.length === 0 && <EmptyText text="Aucun équipement enregistré." t={t} />}
      {equipment.map((item) => {
        const meta = getEquipMeta(item);
        return (
          <DeviceCard key={item.id} icon={meta.icon} color={meta.color} badge={item.status} t={t}>
            <Text style={[styles.deviceName, { color: t.text }]}>{item.name}</Text>
            <Text style={[styles.deviceSub, { color: t.sub }]}>
              {item.equipment_type || "Appareil"} · {fmt(item.rated_power_kw)} kW
            </Text>
          </DeviceCard>
        );
      })}

      <View style={{ height: 20 }} />

      {/* Modal ajout équipement */}
      <Modal
        visible={showModal}
        animationType="slide"
        transparent
        onRequestClose={() => setShowModal(false)}
      >
        <Pressable style={styles.overlay} onPress={() => setShowModal(false)}>
          <KeyboardAvoidingView
            behavior={Platform.OS === "ios" ? "padding" : "height"}
            style={styles.overlayInner}
          >
            <Pressable
              style={[styles.modalCard, { backgroundColor: t.card }]}
              onPress={() => {}}
            >
              {/* Modal header */}
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: t.text }]}>Nouvel équipement</Text>
                <TouchableOpacity onPress={() => setShowModal(false)} style={styles.closeBtn}>
                  <X color={t.sub} size={20} strokeWidth={2.4} />
                </TouchableOpacity>
              </View>

              {/* Champs */}
              <Text style={[styles.fieldLabel, { color: t.sub }]}>Nom *</Text>
              <View style={[styles.inputWrap, { borderColor: t.border }]}>
                <TextInput
                  style={[styles.input, { color: t.text }]}
                  value={form.name}
                  onChangeText={(v) => setForm((f) => ({ ...f, name: v }))}
                  placeholder="Ex : Réfrigérateur, Panneau PV…"
                  placeholderTextColor={t.sub}
                  selectionColor={palette.blue}
                />
              </View>

              <Text style={[styles.fieldLabel, { color: t.sub }]}>Type</Text>
              <View style={styles.typeGrid}>
                {EQUIP_TYPES.map((type) => {
                  const active = form.equipment_type === type;
                  const meta   = EQUIP_ICONS[type] || { color: palette.slate };
                  return (
                    <TouchableOpacity
                      key={type}
                      onPress={() => setForm((f) => ({ ...f, equipment_type: type }))}
                      style={[
                        styles.typeChip,
                        {
                          borderColor: active ? meta.color : t.border,
                          backgroundColor: active ? meta.color + "18" : "transparent",
                        },
                      ]}
                    >
                      <Text style={{ color: active ? meta.color : t.sub, fontSize: 12, fontWeight: "700" }}>
                        {type}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>

              <Text style={[styles.fieldLabel, { color: t.sub }]}>Puissance nominale (kW)</Text>
              <View style={[styles.inputWrap, { borderColor: t.border }]}>
                <TextInput
                  style={[styles.input, { color: t.text }]}
                  value={form.rated_power_kw}
                  onChangeText={(v) => setForm((f) => ({ ...f, rated_power_kw: v }))}
                  placeholder="Ex : 1.5"
                  placeholderTextColor={t.sub}
                  keyboardType="numeric"
                  selectionColor={palette.blue}
                />
              </View>

              <TouchableOpacity
                style={[styles.saveBtn, { opacity: saving ? 0.7 : 1 }]}
                onPress={createEquipment}
                disabled={saving}
                activeOpacity={0.85}
              >
                <Plus color="#fff" size={16} strokeWidth={2.6} />
                <Text style={styles.saveBtnText}>
                  {saving ? "Enregistrement…" : "Ajouter l'équipement"}
                </Text>
              </TouchableOpacity>
            </Pressable>
          </KeyboardAvoidingView>
        </Pressable>
      </Modal>
    </ScreenScroll>
  );
}

/* ── Sub-components ── */

function SectionHeader({ icon: Icon, color, label, count, t }) {
  return (
    <View style={[styles.sectionHeader, { marginTop: 18 }]}>
      <Icon color={color} size={16} strokeWidth={2.4} />
      <Text style={[styles.sectionTitle, { color: t.text }]}>{label}</Text>
      <View style={[styles.countBadge, { backgroundColor: color + "18" }]}>
        <Text style={{ color, fontSize: 11, fontWeight: "700" }}>{count}</Text>
      </View>
    </View>
  );
}

function DeviceCard({ icon: Icon, color, badge, children, t }) {
  return (
    <View style={[styles.deviceCard, { backgroundColor: t.card, borderColor: t.border }]}>
      <View style={[styles.deviceIconWrap, { backgroundColor: color + "15" }]}>
        <Icon color={color} size={18} strokeWidth={2.4} />
      </View>
      <View style={styles.deviceBody}>{children}</View>
      {badge && <Badge value={badge} />}
    </View>
  );
}

function EmptyText({ text, t }) {
  return <Text style={[styles.empty, { color: t.sub }]}>{text}</Text>;
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  addBtn: {
    width: 42, height: 42, borderRadius: 12,
    backgroundColor: palette.blue, alignItems: "center", justifyContent: "center", marginTop: 8,
  },
  sectionHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 },
  sectionTitle: { fontSize: 15, fontWeight: "800", flex: 1 },
  countBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999 },
  empty: { marginBottom: 10, fontSize: 13 },
  deviceCard: {
    flexDirection: "row", alignItems: "center",
    borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 8, gap: 12,
  },
  deviceIconWrap: { width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  deviceBody: { flex: 1 },
  deviceName: { fontWeight: "700", fontSize: 14, marginBottom: 3 },
  deviceSub:  { fontSize: 12, lineHeight: 17 },

  /* Modal */
  overlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", justifyContent: "flex-end" },
  overlayInner: { justifyContent: "flex-end" },
  modalCard: {
    borderTopLeftRadius: 20, borderTopRightRadius: 20,
    padding: 20, paddingBottom: 32,
  },
  modalHeader: {
    flexDirection: "row", justifyContent: "space-between",
    alignItems: "center", marginBottom: 18,
  },
  modalTitle: { fontSize: 17, fontWeight: "800" },
  closeBtn: { width: 34, height: 34, alignItems: "center", justifyContent: "center" },

  fieldLabel: { fontSize: 12, marginBottom: 6, marginTop: 12 },
  inputWrap: {
    borderWidth: 1, borderRadius: 10, minHeight: 46,
    paddingHorizontal: 12, flexDirection: "row", alignItems: "center",
  },
  input: { flex: 1, paddingVertical: 10, fontSize: 14, backgroundColor: "transparent" },

  typeGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 2 },
  typeChip: { borderWidth: 1.5, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 7 },

  saveBtn: {
    backgroundColor: palette.blue, borderRadius: 12, padding: 14, marginTop: 18,
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
  },
  saveBtnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
});
