# Déploiement EC2 (Docker Compose)

Option la plus simple pour démarrer.

1. Lancer une instance EC2 (Ubuntu 22.04, `t3.small`+), SG ouvrant 80/443.
2. Installer Docker + Compose plugin :
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-plugin
   sudo usermod -aG docker $USER
   ```
3. Copier le repo (git clone / scp), créer `.env` à partir de `.env.example`.
4. Renseigner `DATABASE_URL` (RDS), `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
   `CORS_ALLOWED_ORIGINS`, `VITE_API_BASE_URL`.
5. Lancer :
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```
6. HTTPS : pointer un domaine vers l'IP, puis `certbot` sur le conteneur Nginx
   (ou un Nginx hôte) pour Let's Encrypt.
7. Logs : `docker compose -f docker-compose.prod.yml logs -f backend`.
