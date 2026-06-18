# Roadmap de développement

## Réalisé (v1.0)
- Backend Django REST modulaire (10 apps) + JWT + Swagger
- Modèles, serializers, viewsets, endpoints principaux
- Moteur flou initial + décisions persistées
- Prévisions horaires production PV + consommation
- Service MQTT (souscripteur + persistance)
- Frontend React (pages publiques + dashboard complet)
- Mobile Expo (tabs, mode cloud/edge/cache offline)
- Edge gateway (cache SQLite + sync + API locale)
- Docker Compose dev/prod + Nginx + Mosquitto
- Seed de données réalistes

## Perspectives futures
- **Agent conversationnel** (désactivé — voir `future-agent.md`)
- WebSockets temps réel (canal `VITE_WS_URL`)
- Modèles avancés possibles plus tard, gérés côté backend/admin
- Edge computing étendu : inférence locale, file persistante
- Multi-tenant, rôles fins, audit
- Notifications push mobiles complètes (Expo Notifications)
- Rapports PDF
