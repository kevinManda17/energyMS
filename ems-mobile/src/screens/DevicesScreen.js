import { useCallback, useEffect, useRef, useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, Switch,
  StyleSheet, Modal, KeyboardAvoidingView, Platform, Pressable,
} from "react-native";
import {
  Activity,
  CircuitBoard,
  Cpu,
  Lightbulb,
  Plus,
  Power,
  PowerOff,
  Radio,
  Settings2,
  Thermometer,
  X,
  Zap,
} from "lucide-react-native";
import { Badge } from "../components/Badge";
import { ScreenScroll, PageTitle } from "../components/Screen";
import { devicesApi, relaysApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";
import { fmt } from "../utils/format";

const RELAY_LINES = [
  { key: "line1", label: "Ligne 1", desc: "Lampe 10 W + prise 1" },
  { key: "line2", label: "Ligne 2", desc: "Lampe 20 W" },
  { key: "line3", label: "Ligne 3", desc: "Lampe 10 W + prise 2" },
];

/* Qui commande les lignes : l'humain, l'humain sur proposition, ou l'expert. */
const MODES = [
  { key: "MANUAL",   label: "Manuel",   note: "Mode manuel activé." },
  { key: "ASSISTED", label: "Assisté",  note: "Mode assisté : l'expert propose, vous validez." },
  { key: "AUTO",     label: "Auto",     note: "Mode automatique (expert) activé." },
];

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

// Les cinq niveaux de priorité du modèle Equipment, du plus protégé au plus
// délestable. La décision les regroupe en trois catégories, mais l'utilisateur
// choisit bien parmi les cinq. Auparavant la priorité était figée à NORMAL.
const PRIORITIES = [
  { value: "CRITICAL",     label: "Critique",    color: palette.danger },
  { value: "IMPORTANT",    label: "Important",   color: palette.solar },
  { value: "NORMAL",       label: "Normal",      color: palette.green },
  { value: "LOW",          label: "Secondaire",  color: palette.blue },
  { value: "NON_CRITICAL", label: "Non critique", color: palette.slate },
];
const PRIORITY_LABEL = Object.fromEntries(PRIORITIES.map((p) => [p.value, p.label]));

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
  const [form, setForm]           = useState({ name: "", equipment_type: "LOAD", rated_power_kw: "", priority: "NORMAL" });
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
        priority:         form.priority,
        status:   "ACTIVE",
      });
      setForm({ name: "", equipment_type: "LOAD", rated_power_kw: "", priority: "NORMAL" });
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

      {/* Contrôle des lignes (relais ESP32) */}
      {houseId ? <RelayControl houseId={houseId} t={t} /> : null}

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
              {" · "}
              {item.relay_line ? `Ligne ${item.relay_line}` : "ligne non rattachée"}
              {" · "}
              {PRIORITY_LABEL[item.priority] || item.priority || "Normal"}
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

              <Text style={[styles.fieldLabel, { color: t.sub }]}>Priorité</Text>
              <View style={styles.typeGrid}>
                {PRIORITIES.map((p) => {
                  const active = form.priority === p.value;
                  return (
                    <TouchableOpacity
                      key={p.value}
                      onPress={() => setForm((f) => ({ ...f, priority: p.value }))}
                      style={[
                        styles.typeChip,
                        {
                          borderColor: active ? p.color : t.border,
                          backgroundColor: active ? p.color + "18" : "transparent",
                        },
                      ]}
                    >
                      <Text style={{ color: active ? p.color : t.sub, fontSize: 12, fontWeight: "700" }}>
                        {p.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
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

/* ── Contrôle des lignes (relais) ── */

function contactLabel(iso) {
  if (!iso) return "Jamais contacté";
  const diffMs = Date.now() - new Date(iso).getTime();
  if (diffMs < 15000) return "En ligne";
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return `Vu il y a ${Math.max(1, mins)} min`;
  return `Vu le ${new Date(iso).toLocaleDateString("fr-FR")}`;
}

function RelayControl({ houseId, t }) {
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const msgTimer = useRef(null);

  const flash = useCallback((text) => {
    setMsg(text);
    if (msgTimer.current) clearTimeout(msgTimer.current);
    msgTimer.current = setTimeout(() => setMsg(""), 3000);
  }, []);

  const load = useCallback(async () => {
    if (!houseId) return;
    try {
      setState(await relaysApi.get(houseId));
    } catch {
      /* silencieux : la carte affiche l'état connu ou rien */
    }
  }, [houseId]);

  useEffect(() => {
    load();
  }, [load]);

  // Rafraîchit périodiquement pour refléter le dernier contact du nœud.
  useEffect(() => {
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => () => { if (msgTimer.current) clearTimeout(msgTimer.current); }, []);

  async function apply(patch, note) {
    if (!houseId || busy) return;
    setBusy(true);
    try {
      const next = await relaysApi.set(houseId, patch);
      setState(next);
      flash(note || "Commande envoyée.");
    } catch {
      flash("Échec de l'envoi de la commande.");
    } finally {
      setBusy(false);
    }
  }

  // Mode assisté : accepter ou écarter la proposition du système expert.
  async function resolveProposal(action) {
    if (!houseId || busy) return;
    setBusy(true);
    try {
      const next = await relaysApi.resolveProposal(houseId, action);
      setState(next);
      flash(action === "accept"
        ? "Proposition appliquée aux lignes."
        : "Proposition écartée.");
    } catch {
      flash("Échec du traitement de la proposition.");
    } finally {
      setBusy(false);
    }
  }

  const online = state?.last_contact_at
    ? Date.now() - new Date(state.last_contact_at).getTime() < 15000
    : false;
  const allOn = state ? RELAY_LINES.every((l) => state[l.key]) : false;
  const isAuto = state?.control_mode === "AUTO";
  const isAssisted = state?.control_mode === "ASSISTED";
  const pending = isAssisted ? state?.auto_pending_lines : null;

  return (
    <View style={[styles.relayCard, { backgroundColor: t.card, borderColor: t.border }]}>
      <View style={styles.relayHeader}>
        <Power color={palette.blue} size={16} strokeWidth={2.4} />
        <Text style={[styles.relayTitle, { color: t.text }]}>Contrôle des lignes</Text>
        <View style={[styles.onlinePill, { backgroundColor: online ? palette.greenLight : "#F1F5F9" }]}>
          <View style={[styles.onlineDot, { backgroundColor: online ? palette.green : palette.slate }]} />
          <Text style={{ color: online ? palette.green : palette.slate, fontSize: 10, fontWeight: "700" }}>
            {contactLabel(state?.last_contact_at)}
          </Text>
        </View>
      </View>

      {/* Mode : manuel, assisté (l'expert propose) ou auto (l'expert applique). */}
      <View style={[styles.modeRow, { borderColor: t.border }]}>
        {MODES.map((m) => {
          const active = (state?.control_mode || "MANUAL") === m.key;
          return (
            <TouchableOpacity
              key={m.key}
              style={[styles.modeBtn, active && { backgroundColor: palette.blue }]}
              onPress={() => apply({ control_mode: m.key }, m.note)}
              disabled={busy || state == null}
              activeOpacity={0.8}
            >
              <Text style={{ color: active ? "#fff" : t.sub, fontSize: 12, fontWeight: "700" }}>
                {m.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {isAuto && (
        <Text style={[styles.autoHint, { color: palette.blue }]}>
          Le système expert n'agit que sur une condition soutenue (confirmée sur
          quelques minutes), pas sur un déficit passager. Commandes manuelles
          désactivées.
        </Text>
      )}

      {isAssisted && !pending && (
        <Text style={[styles.autoHint, { color: t.sub }]}>
          Le système expert surveille le micro-réseau et vous proposera un
          délestage si nécessaire. Rien n'est coupé sans votre accord.
        </Text>
      )}

      {pending && (
        <View style={[styles.proposalBox, { borderColor: palette.solar }]}>
          <Text style={{ color: palette.solar, fontWeight: "800", fontSize: 13 }}>
            Le système expert propose un changement
          </Text>
          <Text style={{ color: t.sub, fontSize: 12, marginTop: 3, marginBottom: 8 }}>
            {RELAY_LINES.filter((l) => !!state[l.key] !== !!pending[l.key])
              .map((l) => `${l.label} → ${pending[l.key] ? "rétablir" : "couper"}`)
              .join(" · ")}
          </Text>
          <View style={{ flexDirection: "row", gap: 8 }}>
            <TouchableOpacity
              style={[styles.proposalBtn, { backgroundColor: palette.green }]}
              onPress={() => resolveProposal("accept")}
              disabled={busy}
              activeOpacity={0.85}
            >
              <Text style={{ color: "#fff", fontWeight: "800", fontSize: 12 }}>Appliquer</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.proposalBtn, { borderWidth: 1, borderColor: t.border }]}
              onPress={() => resolveProposal("dismiss")}
              disabled={busy}
              activeOpacity={0.85}
            >
              <Text style={{ color: t.sub, fontWeight: "800", fontSize: 12 }}>Ignorer</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {RELAY_LINES.map((line) => {
        const on = !!state?.[line.key];
        return (
          <View key={line.key} style={[styles.relayRow, { borderTopColor: t.border }]}>
            <View style={[styles.relayIcon, { backgroundColor: on ? palette.solarLight : "#F1F5F9" }]}>
              <Lightbulb color={on ? palette.solar : palette.slate} size={17} strokeWidth={2.2} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.relayLabel, { color: t.text }]}>{line.label}</Text>
              <Text style={[styles.relaySub, { color: t.sub }]}>{line.desc}</Text>
              <Text style={{ color: on ? palette.green : palette.slate, fontSize: 11, fontWeight: "700", marginTop: 1 }}>
                {on ? "Connectée" : "Déconnectée"}
              </Text>
            </View>
            <Switch
              value={on}
              disabled={busy || state == null || isAuto}
              onValueChange={(next) =>
                apply({ [line.key]: next }, `${line.label} ${next ? "connectée" : "déconnectée"}.`)
              }
              trackColor={{ false: "#CBD5E1", true: palette.green }}
              thumbColor="#fff"
            />
          </View>
        );
      })}

      {/* Bouton unique : eteint tout si tout est allume, sinon allume tout. */}
      <TouchableOpacity
        style={[
          styles.toggleAllBtn,
          {
            borderColor: allOn ? palette.danger : palette.green,
            opacity: busy || state == null || isAuto ? 0.4 : 1,
          },
        ]}
        onPress={() =>
          apply(
            { line1: !allOn, line2: !allOn, line3: !allOn },
            allOn ? "Toutes les lignes coupées." : "Toutes les lignes allumées."
          )
        }
        disabled={busy || state == null || isAuto}
        activeOpacity={0.85}
      >
        {allOn ? (
          <PowerOff color={palette.danger} size={15} strokeWidth={2.4} />
        ) : (
          <Power color={palette.green} size={15} strokeWidth={2.4} />
        )}
        <Text style={{ color: allOn ? palette.danger : palette.green, fontWeight: "800", fontSize: 13 }}>
          {allOn ? "Tout éteindre" : "Tout allumer"}
        </Text>
      </TouchableOpacity>

      <Text style={[styles.relayHint, { color: t.sub }]}>
        Ordre appliqué par le nœud ESP32 au prochain relevé (~3 s). Le nœud se
        lie automatiquement à ce micro-réseau dès que vous actionnez une ligne —
        aucun jeton à configurer.
      </Text>

      {msg ? <Text style={styles.relayMsg}>{msg}</Text> : null}
    </View>
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

  /* Contrôle des lignes (relais) */
  relayCard: { borderWidth: 1, borderRadius: 14, padding: 14, marginTop: 14, marginBottom: 4 },
  relayHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 },
  relayTitle: { fontSize: 15, fontWeight: "800", flex: 1 },
  onlinePill: {
    flexDirection: "row", alignItems: "center", gap: 5,
    paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999,
  },
  onlineDot: { width: 7, height: 7, borderRadius: 4 },
  relayRow: {
    flexDirection: "row", alignItems: "center", gap: 12,
    paddingVertical: 12, borderTopWidth: 1, marginTop: 8,
  },
  relayIcon: { width: 38, height: 38, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  relayLabel: { fontSize: 14, fontWeight: "700" },
  relaySub: { fontSize: 12, lineHeight: 16 },
  modeRow: {
    flexDirection: "row", borderWidth: 1, borderRadius: 12, overflow: "hidden",
    marginTop: 12,
  },
  modeBtn: {
    flex: 1, alignItems: "center", justifyContent: "center", paddingVertical: 9,
  },
  autoHint: { fontSize: 11, lineHeight: 15, marginTop: 8 },
  proposalBox: {
    borderWidth: 1.5, borderRadius: 12, padding: 12, marginTop: 10,
  },
  proposalBtn: {
    flex: 1, alignItems: "center", justifyContent: "center",
    paddingVertical: 9, borderRadius: 10,
  },
  toggleAllBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    borderWidth: 1.5, borderRadius: 12,
    paddingVertical: 11, marginTop: 12,
  },
  relayHint: { fontSize: 11, lineHeight: 15, marginTop: 8 },
  relayMsg: { fontSize: 12, fontWeight: "700", color: palette.green, marginTop: 8 },
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
