import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, MapPin, Sun, BatteryCharging, Trash2 } from "lucide-react";
import { PageHeader, Loading, Badge, Empty } from "../components/ui";
import { housesApi } from "../api/endpoints";
import { fmt } from "../utils/format";

export default function Houses() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", location: "", pv_capacity_kw: "", battery_capacity_kwh: "" });

  const { data, isLoading } = useQuery({ queryKey: ["houses"], queryFn: housesApi.list });
  const create = useMutation({
    mutationFn: (p) => housesApi.create(p),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["houses"] });
      setShowForm(false);
      setForm({ name: "", location: "", pv_capacity_kw: "", battery_capacity_kwh: "" });
    },
  });
  const remove = useMutation({
    mutationFn: (id) => housesApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["houses"] }),
  });

  if (isLoading) return <Loading />;
  const houses = data?.results || data || [];

  return (
    <>
      <PageHeader
        title="Micro-réseaux"
        subtitle="Gérez vos maisons et micro-réseaux domestiques."
        actions={
          <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
            <Plus size={16} /> Nouveau micro-réseau
          </button>
        }
      />

      {showForm && (
        <form
          className="card mb-6 grid gap-3 p-5 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate({
              ...form,
              pv_capacity_kw: Number(form.pv_capacity_kw) || 0,
              battery_capacity_kwh: Number(form.battery_capacity_kwh) || 0,
            });
          }}
        >
          <input className="input" placeholder="Nom" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <input className="input" placeholder="Localisation" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
          <input className="input" type="number" step="0.1" placeholder="Capacité PV (kW)" value={form.pv_capacity_kw} onChange={(e) => setForm({ ...form, pv_capacity_kw: e.target.value })} />
          <input className="input" type="number" step="0.1" placeholder="Capacité batterie (kWh)" value={form.battery_capacity_kwh} onChange={(e) => setForm({ ...form, battery_capacity_kwh: e.target.value })} />
          <div className="sm:col-span-2">
            <button className="btn-primary" disabled={create.isPending}>Enregistrer</button>
          </div>
        </form>
      )}

      {houses.length === 0 ? (
        <Empty message="Aucun micro-réseau. Créez-en un pour commencer." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {houses.map((h) => (
            <div key={h.id} className="card p-5">
              <div className="flex items-start justify-between">
                <h3 className="text-lg font-semibold text-navy dark:text-white">{h.name}</h3>
                <Badge value={h.status === "ONLINE" ? "ACTIVE" : "INACTIVE"}>
                  {h.status}
                </Badge>
              </div>
              <p className="mt-1 flex items-center gap-1 text-sm text-slate-500">
                <MapPin size={14} /> {h.location || "—"}
              </p>
              <div className="mt-4 flex gap-6 text-sm">
                <span className="flex items-center gap-1 text-energy">
                  <Sun size={16} /> {fmt(h.pv_capacity_kw, 1)} kW
                </span>
                <span className="flex items-center gap-1 text-solar">
                  <BatteryCharging size={16} /> {fmt(h.battery_capacity_kwh, 1)} kWh
                </span>
              </div>
              <button
                className="mt-4 inline-flex items-center gap-1 text-sm text-danger hover:underline"
                onClick={() => remove.mutate(h.id)}
              >
                <Trash2 size={14} /> Supprimer
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
