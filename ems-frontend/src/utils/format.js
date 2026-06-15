export const fmt = (n, digits = 2) =>
  n === null || n === undefined || Number.isNaN(Number(n))
    ? "—"
    : Number(n).toLocaleString("fr-FR", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });

export const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : "—";

export const fmtTime = (iso) =>
  iso ? new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) : "—";

export const ACTION_LABELS = {
  CHARGER_BATTERIE: "Charger la batterie",
  UTILISER_BATTERIE: "Utiliser la batterie",
  ALIMENTER_CHARGES: "Alimenter les charges",
  DELESTER_NON_PRIORITAIRES: "Délester non prioritaires",
  NOTIFIER_UTILISATEUR: "Notifier l'utilisateur",
  ATTENDRE: "Attendre",
};
