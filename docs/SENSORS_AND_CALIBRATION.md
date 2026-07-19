# Capteurs et calibration

> La documentation doit rester alignée sur l'évolution réelle du système. Toute
> modification du câblage, des capteurs, des unités ou des charges doit être
> répercutée ici. Vérification : `python scripts/audit_config.py --strict`

Dernière mise à jour : **19/07/2026**

---

## 1. L'idée à retenir

Le système ne cherche pas à afficher une valeur *idéale*. Il affiche la valeur
**réellement mesurée**, corrigée par un coefficient de calibration fiable.

Une tension n'est donc jamais forcée à 220 V, 224 V ou 215 V. Si la ligne 1
fluctue à 217 V, la ligne 2 à 224 V et la ligne 3 à 210 V, le système doit
afficher **217 / 224 / 210** — pas trois fois la même valeur.

Un plafonnement `[215, 224] V` a existé dans le backend puis a été **retiré** :
il masquait les fluctuations et rendait les trois lignes indiscernables.

---

## 2. Capteurs du prototype

Six capteurs physiques. La **puissance n'est pas un capteur** : elle est
calculée à partir d'une tension et d'un courant.

| Code | Type | Ligne | GPIO | Unité | Modèle |
|------|------|-------|------|-------|--------|
| `V1` | tension | 1 | 34 | V | ZMPT101B |
| `I1` | courant | 1 | 35 | A | ZMCT103C |
| `V2` | tension | 2 | 32 | V | ZMPT101B |
| `I2` | courant | 2 | 33 | A | ZMCT103C |
| `V3` | tension | 3 | 36 (SP/SVP) | V | ZMPT101B |
| `I3` | courant | 3 | 39 (SN/SVN) | A | ZMCT103C |

Puissance par ligne : `V1 + I1 → ligne 1`, `V2 + I2 → ligne 2`, `V3 + I3 → ligne 3`.

Création en base : `python manage.py seed_prototype --house <id>` (idempotent,
n'écrase jamais une calibration déjà saisie).

### Champs d'un capteur

`code`, `name`, `sensor_type`, `line_number`, `gpio_pin`, `unit`, `color`,
`description`, `last_seen_at`, `calibration_factor`, `calibration_offset`,
`calibrated_at`, `calibration_method`, `calibration_status`.

---

## 3. Capteur, charge, relais : ne pas confondre

| Objet | Rôle | Modèle Django |
|-------|------|---------------|
| **Sensor** | *mesure* une grandeur (V1, I1…) | `devices.Sensor` |
| **Equipment / Load** | *consomme* (lampe, prise) | `devices.Equipment` |
| **Relay** | *commande* une ligne | `devices.RelayState` |
| **Measurement** | valeur produite par un capteur | `measurements.Measurement` |
| Puissance de ligne | **calculée** (V × I), pas mesurée | — |

---

## 4. Formule de calibration

```
valeur_physique = valeur_brute_rms × calibration_factor + calibration_offset
```

- `calibration_factor = 1.0` et `offset = 0.0` ⇒ **non calibré** : on lit alors
  le RMS brut de la sortie du capteur (en volts ADC), pas des volts secteur.
- L'`offset` corrige un résidu constant (bruit de fond lu à courant nul). Le
  laisser à 0 tant qu'il n'a pas été mesuré.
- **Un coefficient par capteur.** Deux ZMPT101B n'ont pas le même
  potentiomètre : un coefficient commun est forcément faux sur au moins deux
  lignes.

---

## 5. Calibrer une tension (ZMPT101B)

À refaire **pour chaque ligne**.

1. Alimenter les trois lignes depuis la **même source AC**.
2. Mesurer la tension réelle au multimètre (le même pour les trois).
3. Lire la valeur brute RMS du capteur (`raw_value` de la dernière mesure).
4. Calculer : `CAL_Vx = U_multimètre / U_brute_x`
5. Enregistrer le coefficient (voir §8, l'interface impose une confirmation).
6. Vérifier, puis recommencer si l'écart persiste.

Ne **pas** retoucher le potentiomètre après calibration : cela l'invalide.

---

## 6. Calibrer un courant (ZMCT103C)

1. Brancher une charge connue (lampe 10 W ou 20 W).
2. Courant théorique : `I = P / U`
   - 10 W sous 220 V ≈ **0,045 A**
   - 20 W sous 220 V ≈ **0,091 A**
3. Lire la valeur brute RMS du capteur.
4. Calculer : `CAL_Ix = I_théorique / I_brut`
5. Comparer `CAL_I1`, `CAL_I2`, `CAL_I3`.

### Mesures faibles et astuce des tours

Ces courants sont petits et la mesure est bruitée. On peut faire passer **N
tours du même fil de phase** dans le tore : le capteur voit alors ≈ N × I. La
référence de calibration devient donc :

```
I_reference = N × I_réel
```

L'API prend ce cas en charge via le paramètre `turns`. **Après calibration,
remettre un seul passage.**

> ⚠ Ne **jamais** faire passer la phase ET le neutre ensemble dans le tore :
> les champs s'annulent et le capteur lit ~0.

---

## 7. Détecter un capteur mal réglé (validation croisée)

Des capteurs de même modèle, alimentés pareil, sur des entrées ADC équivalentes
et mesurant la même source doivent avoir des coefficients **proches** — proches,
pas identiques.

Le backend compare chaque coefficient à la **médiane** de ses semblables (les
tensions entre elles, les courants entre eux) :

```
écart_% = |CAL_x − médiane| / médiane × 100
écart_% > 15 %  ->  statut « suspect »
```

**Pourquoi la médiane et non la moyenne.** Un seul coefficient aberrant tire la
moyenne à lui et fait dépasser le seuil aux capteurs sains. Avec
`(126.5, 129.2, 300.0)` : la moyenne vaut 185.2 et **les trois** capteurs sont
déclarés suspects, y compris les deux corrects. La médiane vaut 129.2, et seul
le capteur à 300.0 est signalé — le comportement attendu.

Exemples :

| Coefficients | Verdict |
|--------------|---------|
| 126.5 / 129.2 / 127.8 | cohérent — tous `calibrated` |
| 126.5 / 129.2 / **300.0** | `V3` **suspect** : vérifier le montage |

Un capteur suspect n'est **jamais corrigé automatiquement**. Le statut est un
outil de diagnostic : vérifier le câblage, l'alimentation 3,3 V / 5 V, le GND
commun, le potentiomètre, l'entrée ADC, un mauvais contact, le bruit.

Les capteurs non calibrés (facteur 1.0) sont **exclus** du calcul de la
référence : sinon ils fausseraient la comparaison.

---

## 8. Interface de calibration (API)

Deux étapes, pour qu'aucun coefficient ne s'applique sans validation humaine.

**Proposer** — ne modifie rien :

```http
POST /api/sensors/<id>/calibration/
{"action": "propose", "reference_value": 219.0, "raw_value": 1.84}
```

```json
{"sensor_code": "V1", "proposed_factor": 119.02,
 "current_factor": 1.0, "applied": false}
```

`raw_value` est optionnel : à défaut, la dernière mesure brute du capteur est
utilisée. `turns` pour les capteurs de courant (voir §6).

**Appliquer** — après confirmation de l'utilisateur :

```http
POST /api/sensors/<id>/calibration/
{"action": "apply", "calibration_factor": 119.02, "calibration_offset": 0}
```

La réponse renvoie le nouveau `calibration_status` et un résumé du groupe : un
capteur calibré déplace la médiane, donc tout le groupe est réévalué.

---

## 9. Calibration en deux niveaux

1. **Matériel** — vérifier les branchements, l'alimentation, le GND commun ;
   ajuster les potentiomètres pour obtenir des signaux bruts comparables entre
   V1, V2 et V3.
2. **Logiciel** — appliquer les coefficients, conserver la date et la méthode.

Le système expose toujours : valeur brute, valeur calibrée, coefficient utilisé,
statut de calibration.

---

## 10. Valider après calibration

**Tension** — comparer l'affichage au multimètre. Tolérance prototype : ±2 % à
±5 %. Au-delà, refaire la calibration.

**Courant** — comparer avec une charge connue. Les petites charges donnent des
mesures bruitées : accepter une précision moindre au début.

**Puissance** — repères de test (jamais forcés dans le code) :

| Situation | Ordre de grandeur |
|-----------|-------------------|
| lampe 10 W seule | ≈ 0,010 kW |
| lampe 20 W seule | ≈ 0,020 kW |
| les trois lampes | ≈ 0,040 kW |
| + chargeur 20 W | ≈ 0,060 kW |
| + charge légère | 0,080 à 0,100 kW |

Ce sont des **repères de cohérence**, pas des valeurs à imposer.

---

## 11. État actuel

**Aucun capteur n'est calibré.** Tous les coefficients valent 1.0 : le système
affiche du RMS brut. C'est assumé — mieux vaut une valeur brute reconnue comme
telle qu'un chiffre inventé.

Prochaine étape, côté matériel : calibrer les six capteurs au multimètre selon
§5 et §6, puis vérifier qu'aucun n'est signalé « suspect ».
