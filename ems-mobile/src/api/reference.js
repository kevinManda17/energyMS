/**
 * Référentiel des énumérations — chargé depuis l'API, jamais écrit en dur.
 *
 * LE DÉFAUT CORRIGÉ : les libellés des priorités, des codes de décision, des
 * modes d'exécution et des niveaux d'alerte étaient écrits dans le code du web
 * ET du mobile. Trois listes pour la même énumération — la base, le web, le
 * mobile — et elles ne coïncidaient pas.
 *
 * C'est l'origine du défaut d'affichage des priorités : l'interface montrait
 * « prioritaire » là où la base disait `IMPORTANT`, et une valeur qu'elle ne
 * connaissait pas tombait dans le vide, sans erreur ni trace.
 *
 * Ajouter un niveau de priorité obligeait à modifier trois dépôts ; en oublier
 * un le faisait disparaître de l'affichage. Désormais un ajout se propage sans
 * toucher ni au web ni au mobile.
 *
 * Ce fichier est le PENDANT EXACT de `ems-frontend/src/api/reference.js` : même
 * interface, même comportement. Les deux interfaces doivent afficher les mêmes
 * libellés — c'est tout l'objet de la correction.
 */
import { api } from "./client";

let cache = null;
let enCours = null;

/**
 * Charge le référentiel une fois par session.
 *
 * Les interfaces en ont besoin au démarrage : une requête unique, et un cache
 * mémoire, plutôt qu'un appel par écran. Le référentiel ne change qu'au
 * déploiement.
 */
export async function loadReference() {
  if (cache) return cache;
  if (!enCours) {
    enCours = api
      .get("/reference/")
      .then(({ data }) => {
        cache = data;
        return data;
      })
      .finally(() => {
        enCours = null;
      });
  }
  return enCours;
}

/** Vide le cache — utile après une reconnexion sous un autre compte. */
export function resetReference() {
  cache = null;
}

/**
 * Libellé d'une valeur d'énumération.
 *
 * Renvoie la VALEUR BRUTE quand le référentiel ne la connaît pas, au lieu de
 * renvoyer vide. Une valeur inconnue doit se voir : c'est précisément parce
 * qu'elle disparaissait silencieusement que le défaut d'affichage des
 * priorités est passé inaperçu.
 */
export function labelOf(reference, enumeration, value) {
  if (!value) return "—";
  const entrees = reference?.[enumeration] || [];
  const trouvee = entrees.find((e) => e.value === value);
  return trouvee ? trouvee.label : value;
}

/** Options d'un `<select>`, dans l'ordre servi par l'API. */
export function optionsOf(reference, enumeration) {
  return reference?.[enumeration] || [];
}

/** Unité d'affichage d'une grandeur, portée par le référentiel. */
export function unitOf(reference, quantity) {
  const trouvee = (reference?.quantities || []).find((q) => q.value === quantity);
  return trouvee ? trouvee.unit : "";
}
