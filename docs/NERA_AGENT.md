# N.E.R.A. — agent conversationnel

Assistante vocale du micro-réseau : elle renseigne sur l'installation et
commande les trois lignes électriques à la voix ou au clavier.

Branche : `feat/conversational-agent-nera`
Dernière mise à jour : **19/07/2026**

> **État : backend + interfaces web et mobile faits.** Reste à valider avec une
> vraie clé OpenAI : les tests simulent le client, ils ne prouvent donc pas la
> qualité de compréhension du modèle.

---

## 1. Architecture

```
Voix ──► /api/nera/voice/ ──► Whisper (STT) ──► texte
                                                 │
                                                 ▼
                                    modèle + function calling
                                                 │
                          ┌──────────────────────┴───────────┐
                          ▼                                  ▼
                    outils backend                      réponse texte
              (état, relais, mesures)                        │
                          │                                  ▼
                          ▼                            TTS ──► audio
                  garde-fous vérifiés
```

**Tout se passe côté serveur.** La clé API ne quitte jamais le backend : une clé
embarquée dans une application mobile est une clé publique.

Le modèle **ne touche à rien directement**. Il *demande* un outil, le backend
vérifie les garde-fous puis exécute. Un refus lui est renvoyé comme un résultat
normal, à charge pour lui de l'expliquer à l'utilisateur.

---

## 2. Garde-fous (le point important)

NERA pilote du courant réel. Quatre règles, dans `apps/assistant/tools.py` :

| Règle | Pourquoi |
|-------|----------|
| **Mode AUTO ⇒ refus** | NERA agit au nom de l'utilisateur, donc comme une commande *manuelle*. En mode automatique, l'interface désactive déjà les interrupteurs : la voix ne doit pas contourner le système expert. |
| **Ligne critique jamais coupée** | La reconnaissance vocale se trompe. Couper un équipement vital sur un « éteins tout » mal transcrit est inacceptable. Allumer reste permis. |
| **Une seule maison** | Le micro-réseau vient de la vue (contrôle d'accès), jamais du modèle : NERA ne peut pas agir chez quelqu'un d'autre. |
| **Périmètre limité** | Cinq outils en lecture/commande de relais. Ni suppression, ni modification de calibration, ni accès aux comptes. |

Sur un « éteins tout » avec une ligne critique, NERA éteint les autres, préserve
la critique, et le dit.

Une boucle est bornée à `MAX_TOOL_ROUNDS = 4` allers-retours : un modèle qui
rappelle sans cesse le même outil ferait tourner la requête et la facture.

---

## 3. Outils disponibles

| Outil | Effet |
|-------|-------|
| `get_lines_state` | état des 3 lignes, charges rattachées, mode de contrôle |
| `set_line` | allume/éteint une ligne |
| `set_all_lines` | allume/éteint les trois |
| `get_measurements` | tension, courant, puissance (kW), SOC — signale les capteurs non calibrés |
| `get_expert_decision` | dernière décision du système expert et son explication |

---

## 4. Endpoints

**Texte** — `POST /api/nera/chat/`

```json
{"house": 5, "message": "éteins la lampe de 20 watts"}
```

```json
{"reply": "C'est fait, j'ai éteint la ligne 2.",
 "actions": [{"tool": "set_line", "arguments": {"line": 2, "on": false},
              "result": {"ligne": 2, "allumee": false}}]}
```

`actions` liste ce qui a **réellement** été exécuté : à afficher, et utile pour
la traçabilité (ne pas croire le texte du modèle sur parole).

**Voix** — `POST /api/nera/voice/` (multipart : `house`, `audio`, `speak?`)
Transcription → raisonnement → action → réponse. Avec `speak=true`, la réponse
audio est renvoyée en base64 (`audio_base64`), sans second appel.

**Synthèse seule** — `POST /api/nera/speak/` `{text}` → `audio/mpeg`.
Pour relire une alerte ou une recommandation sans repasser par le modèle.

---

## 5. Configuration

Dans `ems-backend/.env` :

```env
OPENAI_API_KEY=sk-...
NERA_CHAT_MODEL=gpt-4o-mini
NERA_STT_MODEL=whisper-1
NERA_TTS_MODEL=tts-1
NERA_TTS_VOICE=nova
```

Les modèles sont **paramétrables** : l'offre OpenAI évolue vite, rien n'est figé
dans le code. Vérifier les noms et tarifs en vigueur avant mise en service.

**Sans clé**, `/api/nera/*` répond **503** avec un message explicite ; tout le
reste de l'application fonctionne normalement.

---

## 6. Essayer

```bash
curl -X POST http://192.168.84.117:8000/api/nera/chat/ \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"house": 5, "message": "quelles lampes sont allumées ?"}'
```

---

## 7. Interfaces

**Web** — page « N.E.R.A. » dans le menu latéral. Conversation au clavier,
suggestions au premier lancement, et affichage des actions **réellement
exécutées** (on n'affiche pas ce que le modèle *dit* avoir fait, mais ce que le
backend a fait).

> ⚠ **Le micro est bloqué sur le LAN en HTTP.** Les navigateurs exigent un
> contexte sécurisé (HTTPS ou `localhost`) pour `getUserMedia` — exactement la
> même contrainte que la géolocalisation. Sur `http://192.168.84.117:5173`, le
> bouton micro est désactivé avec l'explication affichée ; le clavier fonctionne
> normalement. Pour parler : utiliser le mobile, ou servir le web en HTTPS.

**Mobile** — écran « N.E.R.A. » (onglet *Plus*). C'est **là que la voix prend
tout son sens** : une application native n'a pas la contrainte HTTPS. Micro
(permission demandée au premier usage), transcription, action, et la réponse est
**jouée à voix haute** automatiquement.

Le lecteur audio est libéré en quittant l'écran, sinon une réponse continuerait
de jouer après la navigation.

---

## 8. Limites connues

- **Pas de mot d'éveil** : dire « NERA » ne déclenche rien ; il faut lancer
  l'enregistrement explicitement. Un vrai *wake word* demande une écoute
  permanente côté client.
- **Micro web indisponible en HTTP sur le LAN** (voir §7).
- **Latence** : trois appels réseau en chaîne (STT, chat, TTS). Compter quelques
  secondes. Les API temps réel d'OpenAI réduiraient cela, au prix d'une
  architecture WebSocket.
- **Coût par requête** : chaque commande vocale est facturée trois fois (STT,
  chat, TTS). À surveiller si l'usage devient fréquent.
- **Valeurs non calibrées** : NERA lit les mesures telles quelles. Tant que les
  capteurs ne sont pas calibrés, elle le précise, mais elle ne peut pas corriger.
- **Aucun test avec la vraie API** : la suite simule le client OpenAI. Ce qui est
  vérifié, ce sont les garde-fous et l'exécution des outils — pas la qualité de
  compréhension du modèle, qui demande un essai réel.
