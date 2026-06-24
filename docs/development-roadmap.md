# Roadmap de developpement

## Realise

- Backend Django REST modulaire avec JWT et Swagger.
- Authentification : inscription, connexion, profil, verification telephone, verification e-mail, reset password, changement de mot de passe.
- Micro-reseaux `House` separes des actifs physiques `EnergyAsset`.
- Actifs energetiques : panneaux PV, batteries, onduleurs, regulateurs, reseau, generateurs.
- Capteurs relies aux maisons et optionnellement aux actifs energetiques.
- Equipements/charges avec priorites energetiques.
- Mesures IoT historisees et filtrees par maison, capteur, type et periode.
- MQTT + Edge Gateway avec cache SQLite et synchronisation differee.
- Forecasting par inference : modeles pre-entraines importes + fallback `HourlyProfileForecast`.
- Decisions floues explicables reliees aux previsions.
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
