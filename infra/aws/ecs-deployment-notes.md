# Déploiement ECS Fargate

Pour une production scalable et managée.

1. **ECR** : créer des repos et pousser les images.
   ```bash
   aws ecr create-repository --repository-name ems-backend
   docker build -t ems-backend ./ems-backend
   docker tag ems-backend <acct>.dkr.ecr.<region>.amazonaws.com/ems-backend
   docker push <acct>.dkr.ecr.<region>.amazonaws.com/ems-backend
   ```
2. **Task definitions** :
   - `backend` : commande gunicorn, port 8000, variables d'env via Secrets Manager.
   - `mqtt_worker` : commande `python manage.py run_mqtt`.
   - `mqtt` : image `eclipse-mosquitto` (ou AWS IoT Core en alternative).
3. **Service + ALB** : ALB HTTPS (certificat ACM) → service backend. Health check
   sur `/api/schema/`.
4. **Base** : RDS PostgreSQL (voir notes dédiées).
5. **Migrations** : tâche one-off `python manage.py migrate` au déploiement.
6. **Frontend** : hébergé sur Vercel (ou S3 + CloudFront).
7. CORS : `CORS_ALLOWED_ORIGINS` = domaine du frontend.
