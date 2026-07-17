import { useState } from "react";
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  Modal, KeyboardAvoidingView, Platform, Pressable,
} from "react-native";
import {
  Battery, CheckCircle2, Crosshair, HousePlug, MapPin, Pencil, Plus, Wifi, X, Zap,
} from "lucide-react-native";
import * as Location from "expo-location";
import { Badge } from "../components/Badge";
import { FormInput } from "../components/FormInput";
import { Screen, PageTitle } from "../components/Screen";
import { housesApi } from "../api/endpoints";
import { useActiveHouse } from "../hooks/useActiveHouse";
import { useTheme } from "../hooks/useTheme";
import { palette } from "../theme/colors";

const PAGE_SIZE = 9;

export default function HousesScreen() {
  const t = useTheme();
  const { houses, houseId, setHouseId, reload } = useActiveHouse();
  const [name, setName]         = useState("");
  const [location, setLocation] = useState("");
  const [latitude, setLatitude]   = useState("");
  const [longitude, setLongitude] = useState("");
  const [pvCapacity, setPvCapacity] = useState("");
  const [batteryCapacity, setBatteryCapacity] = useState("");
  const [editing, setEditing]   = useState(null); // maison en cours d'édition
  const [error, setError]       = useState("");
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving]     = useState(false);
  const [locating, setLocating] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  // Renseigne lat/lon depuis le GPS de l'appareil. C'est ici, sur mobile, que
  // la géolocalisation a le plus de sens : l'appareil est physiquement sur le
  // site. Pour une maison distante, on saisit les coordonnées à la main.
  async function useMyPosition() {
    setError("");
    setLocating(true);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        setError("Autorisation de localisation refusée.");
        return;
      }
      const pos = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
      setLatitude(pos.coords.latitude.toFixed(6));
      setLongitude(pos.coords.longitude.toFixed(6));
    } catch {
      setError("Position indisponible. Activez le GPS ou saisissez à la main.");
    } finally {
      setLocating(false);
    }
  }

  function openCreate() {
    setEditing(null);
    setName(""); setLocation("");
    setLatitude(""); setLongitude("");
    setPvCapacity(""); setBatteryCapacity("");
    setError("");
    setShowModal(true);
  }

  // La configuration solaire peut changer (panneau remplacé, capacité
  // ré-estimée, site déplacé) : tout reste modifiable après création.
  function openEdit(house) {
    setEditing(house);
    setName(house.name || "");
    setLocation(house.location || "");
    setLatitude(house.latitude != null ? String(house.latitude) : "");
    setLongitude(house.longitude != null ? String(house.longitude) : "");
    setPvCapacity(house.pv_capacity_kw != null ? String(house.pv_capacity_kw) : "");
    setBatteryCapacity(
      house.battery_capacity_kwh != null ? String(house.battery_capacity_kwh) : ""
    );
    setError("");
    setShowModal(true);
  }

  const toNumber = (v) => (v === "" ? null : Number(String(v).replace(",", ".")));

  async function saveHouse() {
    if (!name.trim()) return;
    setError("");
    setSaving(true);
    const payload = {
      name,
      location,
      latitude: toNumber(latitude),
      longitude: toNumber(longitude),
      pv_capacity_kw: toNumber(pvCapacity),
      battery_capacity_kwh: toNumber(batteryCapacity),
    };
    try {
      if (editing) {
        await housesApi.patch(editing.id, payload);
      } else {
        await housesApi.create({ ...payload, status: "ONLINE" });
      }
      setShowModal(false);
      await reload();
    } catch {
      setError(
        editing
          ? "Modification impossible. Vérifiez la connexion."
          : "Création impossible. Vérifiez la connexion."
      );
    } finally {
      setSaving(false);
    }
  }

  const paged    = houses.slice(0, visibleCount);
  const hasMore  = houses.length > visibleCount;
  const remaining = houses.length - visibleCount;

  return (
    <Screen>
      <View style={styles.headerRow}>
        <PageTitle
          title="Micro-réseaux"
          subtitle={`${houses.length} réseau${houses.length !== 1 ? "x" : ""}`}
        />
        <TouchableOpacity
          style={styles.addBtn}
          onPress={openCreate}
          activeOpacity={0.8}
        >
          <Plus color="#fff" size={18} strokeWidth={2.6} />
        </TouchableOpacity>
      </View>

      <FlatList
        data={paged}
        keyExtractor={(item) => String(item.id)}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={styles.emptyWrap}>
            <HousePlug color={t.sub} size={40} strokeWidth={1.5} />
            <Text style={[styles.emptyText, { color: t.sub }]}>
              Aucun micro-réseau.{"\n"}Appuyez sur + pour en créer un.
            </Text>
          </View>
        }
        renderItem={({ item }) => {
          const isActive = item.id === houseId;
          return (
            <TouchableOpacity onPress={() => setHouseId(item.id)} activeOpacity={0.75}>
              <View style={[
                styles.houseCard,
                {
                  backgroundColor: t.card,
                  borderColor: isActive ? palette.blue : t.border,
                  borderWidth: isActive ? 2 : 1,
                },
              ]}>
                <View style={[styles.statusStrip, {
                  backgroundColor: item.status === "ONLINE" ? palette.green : palette.slate,
                }]} />
                <View style={styles.houseContent}>
                  <View style={styles.houseTop}>
                    <View style={[styles.houseIconWrap, {
                      backgroundColor: isActive ? palette.blueLight : t.muted || "#F1F5F9",
                    }]}>
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
                    <TouchableOpacity
                      onPress={() => openEdit(item)}
                      style={[styles.editBtn, { borderColor: t.border }]}
                      accessibilityLabel={`Modifier ${item.name}`}
                    >
                      <Pencil color={t.sub} size={15} strokeWidth={2.2} />
                    </TouchableOpacity>
                    {isActive
                      ? <CheckCircle2 color={palette.blue} size={22} strokeWidth={2.4} />
                      : <Badge value={item.status} />}
                  </View>
                  <View style={[styles.capacityRow, { borderTopColor: t.border }]}>
                    <CapacityItem icon={Zap}     label="PV"      value={`${item.pv_capacity_kw || 0} kW`}    color={palette.green}  />
                    <Sep t={t} />
                    <CapacityItem icon={Battery} label="Batterie" value={`${item.battery_capacity_kwh || 0} kWh`} color={palette.solar} />
                    <Sep t={t} />
                    <CapacityItem icon={Wifi}    label="Statut"  value={item.status || "—"}                  color={item.status === "ONLINE" ? palette.green : palette.slate} />
                  </View>
                </View>
              </View>
            </TouchableOpacity>
          );
        }}
        ListFooterComponent={
          hasMore ? (
            <TouchableOpacity
              style={[styles.loadMoreBtn, { borderColor: t.border }]}
              onPress={() => setVisibleCount((c) => c + PAGE_SIZE)}
              activeOpacity={0.75}
            >
              <Text style={{ color: palette.blue, fontWeight: "700", fontSize: 14 }}>
                Voir {remaining} de plus
              </Text>
            </TouchableOpacity>
          ) : null
        }
      />

      {/* Modal création */}
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
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: t.text }]}>
                  {editing ? `Modifier « ${editing.name} »` : "Nouveau micro-réseau"}
                </Text>
                <TouchableOpacity onPress={() => setShowModal(false)} style={styles.closeBtn}>
                  <X color={t.sub} size={20} strokeWidth={2.4} />
                </TouchableOpacity>
              </View>

              <FormInput
                icon={HousePlug}
                value={name}
                onChangeText={setName}
                placeholder="Nom (ex: Résidence Lubumbashi)"
                label="Nom du réseau *"
              />
              <FormInput
                icon={MapPin}
                value={location}
                onChangeText={setLocation}
                placeholder="Localisation (ex: Lubumbashi, RDC)"
                label="Localisation"
              />
              <View style={styles.fieldRow}>
                <FormInput
                  icon={MapPin}
                  value={latitude}
                  onChangeText={setLatitude}
                  placeholder="-4.3276"
                  label="Latitude (météo)"
                  keyboardType="numbers-and-punctuation"
                  containerStyle={styles.fieldHalf}
                />
                <FormInput
                  icon={MapPin}
                  value={longitude}
                  onChangeText={setLongitude}
                  placeholder="15.3136"
                  label="Longitude (météo)"
                  keyboardType="numbers-and-punctuation"
                  containerStyle={styles.fieldHalf}
                />
              </View>
              <TouchableOpacity
                style={[styles.geoBtn, { borderColor: palette.blue, opacity: locating ? 0.6 : 1 }]}
                onPress={useMyPosition}
                disabled={locating}
                activeOpacity={0.8}
              >
                <Crosshair color={palette.blue} size={15} strokeWidth={2.4} />
                <Text style={{ color: palette.blue, fontWeight: "700", fontSize: 13 }}>
                  {locating ? "Localisation…" : "Utiliser ma position actuelle"}
                </Text>
              </TouchableOpacity>
              <View style={styles.fieldRow}>
                <FormInput
                  icon={Zap}
                  value={pvCapacity}
                  onChangeText={setPvCapacity}
                  placeholder="ex: 0.3"
                  label="Capacité PV (kWc)"
                  keyboardType="decimal-pad"
                  containerStyle={styles.fieldHalf}
                />
                <FormInput
                  icon={Battery}
                  value={batteryCapacity}
                  onChangeText={setBatteryCapacity}
                  placeholder="ex: 10"
                  label="Batterie (kWh)"
                  keyboardType="decimal-pad"
                  containerStyle={styles.fieldHalf}
                />
              </View>
              <Text style={[styles.capacityHint, { color: t.sub }]}>
                La capacité PV estimée sert à aligner les prévisions solaires
                sur votre installation — modifiable à tout moment.
              </Text>
              {error ? <Text style={styles.formError}>{error}</Text> : null}

              <TouchableOpacity
                style={[styles.saveBtn, { opacity: saving ? 0.7 : 1 }]}
                onPress={saveHouse}
                disabled={saving}
                activeOpacity={0.85}
              >
                <HousePlug color="#fff" size={16} strokeWidth={2.4} />
                <Text style={styles.saveBtnText}>
                  {saving
                    ? "Enregistrement…"
                    : editing ? "Enregistrer les modifications" : "Créer le micro-réseau"}
                </Text>
              </TouchableOpacity>
            </Pressable>
          </KeyboardAvoidingView>
        </Pressable>
      </Modal>
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

function Sep({ t }) {
  return <View style={[styles.capacitySep, { backgroundColor: t.border }]} />;
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  addBtn: {
    width: 42, height: 42, borderRadius: 12,
    backgroundColor: palette.blue, alignItems: "center", justifyContent: "center", marginTop: 8,
  },
  emptyWrap: { alignItems: "center", marginTop: 60, gap: 14 },
  emptyText: { textAlign: "center", fontSize: 15, lineHeight: 22 },

  houseCard: {
    borderRadius: 14, marginBottom: 12, overflow: "hidden", flexDirection: "row",
  },
  statusStrip: { width: 5 },
  houseContent: { flex: 1, padding: 14 },
  houseTop: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 12 },
  houseIconWrap: {
    width: 42, height: 42, borderRadius: 12, alignItems: "center", justifyContent: "center",
  },
  houseName: { fontSize: 16, fontWeight: "800", marginBottom: 3 },
  editBtn: {
    width: 32, height: 32, borderRadius: 8, borderWidth: 1,
    alignItems: "center", justifyContent: "center", marginRight: 8,
  },
  fieldRow: { flexDirection: "row", gap: 10 },
  fieldHalf: { flex: 1 },
  geoBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    borderWidth: 1.5, borderRadius: 12, paddingVertical: 10, marginTop: 4,
  },
  capacityHint: { marginTop: 8, fontSize: 11, lineHeight: 15 },
  locationRow: { flexDirection: "row", alignItems: "center", gap: 4 },
  locationText: { fontSize: 12 },
  capacityRow: {
    flexDirection: "row", alignItems: "center",
    borderTopWidth: 1, paddingTop: 10, gap: 8,
  },
  capacityItem: { flex: 1, alignItems: "center", flexDirection: "row", gap: 5, justifyContent: "center" },
  capacitySep: { width: 1, height: 20 },

  loadMoreBtn: {
    borderWidth: 1, borderRadius: 12, padding: 14,
    alignItems: "center", marginBottom: 12,
  },

  /* Modal */
  overlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", justifyContent: "flex-end" },
  overlayInner: { justifyContent: "flex-end" },
  modalCard: {
    borderTopLeftRadius: 20, borderTopRightRadius: 20,
    padding: 20, paddingBottom: 32,
  },
  modalHeader: {
    flexDirection: "row", justifyContent: "space-between",
    alignItems: "center", marginBottom: 14,
  },
  modalTitle: { fontSize: 17, fontWeight: "800" },
  closeBtn: { width: 34, height: 34, alignItems: "center", justifyContent: "center" },

  formError: { color: palette.danger, marginTop: 8, fontWeight: "600" },
  saveBtn: {
    backgroundColor: palette.blue, flexDirection: "row", alignItems: "center",
    justifyContent: "center", gap: 6, padding: 14, borderRadius: 12, marginTop: 16,
  },
  saveBtnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
});
