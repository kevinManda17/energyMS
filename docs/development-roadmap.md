# Roadmap de developpement

## Realise

- Backend Django REST modulaire avec JWT et Swagger.
- Authentification : inscription, connexion, profil, verification telephone, verification e-mail, reset password, changement de mot de passe.
- Micro-reseaux `House` separes des actifs physiques `EnergyAsset`.
- Actifs energetiques : panneaux PV, batteries, onduleurs, regulateurs, reseau, generateurs.
- Capteurs relies aux maisons et optionnellement aux actifs energetiques.
- Equipements/charges avec priorites energetiques.
- Mesures IoT historisees et filtrees par maison, capteur, type et periode.
- Ingestion temps quasi reel du noeud ESP32 : le releve 3-lignes recu sur `/ems/decision/` est persiste comme mesures (consommation, tension, courant).
- Commande des 3 lignes/relais depuis le web et le mobile (`/houses/{id}/relays/`), appliquee par l'ESP32.
- Collecte meteo Open-Meteo non-bloquante, ciblee sur les micro-reseaux consultes recemment.
- MQTT + Edge Gateway avec cache SQLite et synchronisation differee (module present, non integre a la demo).
- Forecasting par inference : modeles pre-entraines enregistres via `register_models` (GRU consommation, RF production ; LSTM en reference). Pas de repli mathematique.
- Decisions floues explicables calculees sur les mesures reelles, reliees aux previsions.
- Alertes reliees aux decisions.
- Rapports journaliers et exports CSV historises via `DataExport`.
- Frontend React : dashboard, mesures, previsions, decisions, alertes, rapports, parametres.
- Mobile Expo : dashboard condense, navigation, API cloud/edge/local, cache et reglages.
- Docker Compose dev/prod + Nginx + Mosquitto.
- Seed de donnees realistes coherent avec le modele cible.

## Perspectives futures

- Agent conversationnel explicatif, conserve hors coeur actuel.
- WebSockets temps reel.
- Inference locale edge avancee.
- Notifications push mobiles completes.
- Rapports PDF.
- API meteo/solaire optionnelle.
- Multi-tenant avance, roles fins et audit.
