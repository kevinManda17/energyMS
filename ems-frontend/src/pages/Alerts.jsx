import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { PageHeader, Loading, Badge, Empty } from "../components/ui";
import { alertsApi } from "../api/endpoints";
import { fmtDate } from "../utils/format";

export default function Alerts() {
  const qc = useQueryClient();
  const [unreadOnly, setUnreadOnly] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["alerts", unreadOnly],
    queryFn: () => (unreadOnly ? alertsApi.unread() : alertsApi.list({ page_size: 100 })),
  });

  const ack = useMutation({
    mutationFn: (id) => alertsApi.acknowledge(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  if (isLoading) return <Loading />;
  const alerts = data?.results || data || [];

  return (
    <>
      <PageHeader
        title="Alertes"
        subtitle="Notifications critiques, avertissements et informations."
        actions={
          <button
            className={unreadOnly ? "btn-primary" : "btn-ghost"}
            onClick={() => setUnreadOnly((s) => !s)}
          >
            {unreadOnly ? "Toutes les alertes" : "Non lues seulement"}
          </button>
        }
      />

      {alerts.length === 0 ? (
        <Empty message="Aucune alerte." />
      ) : (
        <div className="space-y-3">
          {alerts.map((a) => (
            <div key={a.id} className="card flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <Badge value={a.severity} />
                <div>
                  <div className={`font-medium ${a.is_read ? "text-slate-400" : ""}`}>
                    {a.message}
                  </div>
                  <div className="text-xs text-slate-400">
                    {a.alert_type} · {fmtDate(a.created_at)}
                  </div>
                </div>
              </div>
              {!a.is_read && (
                <button className="btn-ghost" onClick={() => ack.mutate(a.id)}>
                  <Check size={16} /> Acquitter
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
