import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BatteryCharging,
  MapPin,
  Network,
  Pencil,
  Plus,
  Sun,
  Trash2,
  Wifi,
  WifiOff,
} from "lucide-react";
import { PageHeader, Loading, Badge, Empty, Pagination } from "../components/ui";
import { housesApi } from "../api/endpoints";
import { fmt } from "../utils/format";

const HOUSES_PER_PAGE = 9;

const EMPTY_FORM = {
  name: "", location: "", latitude: "", longitude: "",
  pv_capacity_kw: "", battery_capacity_kwh: "",
};

// La configuration d'un micro-réseau (panneau, batterie, position) peut
// changer : tout reste modifiable après création.
export default function Houses() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null); // maison en cours d'édition
  const [form, setForm] = useState(EMPTY_FORM);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({ queryKey: ["houses"], queryFn: housesApi.list });

  function closeForm() {
    setShowForm(false);
    setEditing(null);
    setForm(EMPTY_FORM);
  }

  const save = useMutation({
    mutationFn: (p) => (editing ? housesApi.patch(editing.id, p) : housesApi.create(p)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["houses"] });
      qc.invalidateQueries({ queryKey: ["predict"] });
      closeForm();
    },
  });

  const remove = useMutation({
    mutationFn: (id) => housesApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["houses"] }),
  });

  function openEdit(h) {
    setEditing(h);
    setForm({
      name: h.name || "",
      location: h.location || "",
      latitude: h.latitude ?? "",
      longitude: h.longitude ?? "",
      pv_capacity_kw: h.pv_capacity_kw ?? "",
      battery_capacity_kwh: h.battery_capacity_kwh ?? "",
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  if (isLoading) return <Loading />;
  const houses   = data?.results || data || [];
  const safePage = Math.min(page, Math.max(1, Math.ceil(houses.length / HOUSES_PER_PAGE)));
  const paged    = houses.slice((safePage - 1) * HOUSES_PER_PAGE, safePage * HOUSES_PER_PAGE);

  function handleDelete(h) {
    if (!window.confirm(`Supprimer « ${h.name} » ? Cette action est irréversible.`)) return;
    remove.mutate(h.id);
  }

  return (
    <>
      <PageHeader
        title="Micro-réseaux"
        subtitle="Gérez vos maisons et micro-réseaux domestiques."
        actions={
          <button
            className="btn-primary gap-2"
            onClick={() => (showForm ? closeForm() : setShowForm(true))}
          >
            <Plus size={16} /> Nouveau micro-réseau
          </button>
        }
      />

      {/* Formulaire création / édition */}
      {showForm && (
        <form
          className="card mb-6 p-5"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate({
              name: form.name,
              location: form.location,
              latitude:  form.latitude  === "" ? null : Number(form.latitude),
              longitude: form.longitude === "" ? null : Number(form.longitude),
              pv_capacity_kw:       form.pv_capacity_kw       === "" ? null : Number(form.pv_capacity_kw),
              battery_capacity_kwh: form.battery_capacity_kwh === "" ? null : Number(form.battery_capacity_kwh),
            });
          }}
        >
          <h3 className="mb-4 font-semibold text-navy dark:text-white">
            {editing ? `Modifier « ${editing.name} »` : "Nouveau micro-réseau"}
          </h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="Nom du réseau"
              required
              placeholder="ex: Résidence Lubumbashi"
              value={form.name}
              onChange={(v) => setForm({ ...form, name: v })}
            />
            <FormField
              label="Localisation"
              placeholder="ex: Lubumbashi, RDC"
              value={form.location}
              onChange={(v) => setForm({ ...form, location: v })}
            />
            <FormField
              label="Latitude (météo du site)"
              type="number"
              step="any"
              placeholder="ex: -4.3276"
              value={form.latitude}
              onChange={(v) => setForm({ ...form, latitude: v })}
            />
            <FormField
              label="Longitude (météo du site)"
              type="number"
              step="any"
              placeholder="ex: 15.3136"
              value={form.longitude}
              onChange={(v) => setForm({ ...form, longitude: v })}
            />
            <FormField
              label="Capacité PV estimée (kWc)"
              type="number"
              step="0.05"
              min="0"
              placeholder="ex: 0.3"
              value={form.pv_capacity_kw}
              onChange={(v) => setForm({ ...form, pv_capacity_kw: v })}
            />
            <FormField
              label="Capacité batterie (kWh)"
              type="number"
              step="0.1"
              min="0"
              placeholder="ex: 10.0"
              value={form.battery_capacity_kwh}
              onChange={(v) => setForm({ ...form, battery_capacity_kwh: v })}
            />
          </div>
          <div className="mt-4 flex items-center gap-3">
            <button className="btn-primary" disabled={save.isPending}>
              {save.isPending
                ? "Enregistrement…"
                : editing ? "Enregistrer les modifications" : "Enregistrer"}
            </button>
            <button type="button" className="btn-ghost" onClick={closeForm}>
              Annuler
            </button>
          </div>
        </form>
      )}

      {houses.length === 0 ? (
        <Empty message="Aucun micro-réseau. Créez-en un pour commencer." />
      ) : (
        <>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {paged.map((h) => {
            const online = h.status === "ONLINE";
            return (
              <div
                key={h.id}
                className="card overflow-hidden border-l-4"
                style={{ borderLeftColor: online ? "#16A34A" : "#94A3B8" }}
              >
                {/* Header */}
                <div className="flex items-start justify-between p-5 pb-3">
                  <div className="flex items-start gap-3">
                    <span
                      className={`mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl ${
                        online
                          ? "bg-green-50 dark:bg-green-500/10"
                          : "bg-slate-100 dark:bg-white/5"
                      }`}
                    >
                      {online
                        ? <Wifi size={17} className="text-energy" strokeWidth={2.2} />
                        : <WifiOff size={17} className="text-slate-400" strokeWidth={2.2} />}
                    </span>
                    <div>
                      <h3 className="font-bold text-navy dark:text-white">{h.name}</h3>
                      {h.location && (
                        <p className="flex items-center gap-1 text-xs text-slate-400">
                          <MapPin size={12} /> {h.location}
                        </p>
                      )}
                    </div>
                  </div>
                  <Badge value={h.status === "ONLINE" ? "ACTIVE" : "INACTIVE"}>
                    {h.status}
                  </Badge>
                </div>

                {/* Capacités */}
                <div className="mx-5 mb-4 grid grid-cols-2 gap-2 rounded-xl border border-slate-100 p-3 dark:border-white/5">
                  <CapacityItem
                    icon={Sun}
                    label="Capacité PV"
                    value={`${fmt(h.pv_capacity_kw, 1)} kW`}
                    color="text-energy"
                    bg="bg-green-50 dark:bg-green-500/10"
                  />
                  <CapacityItem
                    icon={BatteryCharging}
                    label="Batterie"
                    value={`${fmt(h.battery_capacity_kwh, 1)} kWh`}
                    color="text-solar"
                    bg="bg-amber-50 dark:bg-amber-500/10"
                  />
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 dark:border-white/5">
                  <span className="flex items-center gap-1.5 text-xs text-slate-400">
                    <Network size={13} strokeWidth={2.2} />
                    ID #{h.id}
                  </span>
                  <div className="flex items-center gap-4">
                    <button
                      className="flex items-center gap-1 text-xs font-medium text-electric opacity-80 transition hover:opacity-100"
                      onClick={() => openEdit(h)}
                    >
                      <Pencil size={13} strokeWidth={2.4} /> Modifier
                    </button>
                    <button
                      className="flex items-center gap-1 text-xs font-medium text-danger opacity-70 transition hover:opacity-100"
                      onClick={() => handleDelete(h)}
                      disabled={remove.isPending}
                    >
                      <Trash2 size={13} strokeWidth={2.4} /> Supprimer
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        {houses.length > HOUSES_PER_PAGE && (
          <Pagination page={safePage} total={houses.length} perPage={HOUSES_PER_PAGE} onChange={setPage} />
        )}
        </>
      )}
    </>
  );
}

function CapacityItem({ icon: Icon, label, value, color, bg }) {
  return (
    <div className={`flex items-center gap-2 rounded-lg ${bg} px-2.5 py-2`}>
      <Icon size={14} className={color} strokeWidth={2.2} />
      <div>
        <p className="text-[10px] text-slate-400">{label}</p>
        <p className={`text-xs font-bold ${color}`}>{value}</p>
      </div>
    </div>
  );
}

function FormField({ label, required, type = "text", step, min, placeholder, value, onChange }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}{required && " *"}
      </span>
      <input
        type={type}
        step={step}
        min={min}
        className="input"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
      />
    </label>
  );
}
