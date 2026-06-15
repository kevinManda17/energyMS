export const fmt = (n, d = 2) =>
  n === null || n === undefined || Number.isNaN(Number(n))
    ? "—"
    : Number(n).toFixed(d);

export const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleString("fr-FR") : "—";

export const ACTION_LABELS = {
  CHARGER_BATTERIE: "Charger la batterie",
  UTILISER_BATTERIE: "Utiliser la batterie",
  ALIMENTER_CHARGES: "Alimenter les charges",
  DELESTER_NON_PRIORITAIRES: "Délester non prioritaires",
  NOTIFIER_UTILISATEUR: "Notifier l'utilisateur",
  ATTENDRE: "Attendre",
};
