# Déploiement AWS — vue d'ensemble

Cible production : **AWS**. Deux options de calcul documentées (EC2 simple ou
ECS Fargate), une base **RDS PostgreSQL**, et **S3 + CloudFront** pour les assets.

```
Vercel (frontend)  ─HTTPS─▶  ALB / Nginx  ─▶  Backend (EC2 ou ECS)  ─▶  RDS PostgreSQL
                                                     │
                                                     └─▶  S3 (media/static) + CloudFront
```

Fichiers :
- `rds-postgresql-notes.md`
- `ec2-deployment-notes.md`
- `ecs-deployment-notes.md`
- `s3-cloudfront-notes.md`

Checklist :
1. RDS PostgreSQL provisionné, `DATABASE_URL` récupéré.
2. Secrets dans AWS SSM/Secrets Manager (`DJANGO_SECRET_KEY`, etc.).
3. Backend déployé (EC2 ou ECS) avec `DJANGO_SETTINGS_MODULE=config.settings.production`.
4. TLS via ACM (ALB) ou certbot (Nginx).
5. `CORS_ALLOWED_ORIGINS` = domaine Vercel.
