# S3 + CloudFront

## Static / media Django
1. Bucket S3 `ems-static` (+ `ems-media`).
2. Utiliser `django-storages` + `boto3` (à ajouter à `requirements.txt`) et
   configurer `STORAGES` en production pour servir `static`/`media` depuis S3.
3. Distribution CloudFront devant le bucket (cache + HTTPS).

## Frontend (alternative à Vercel)
1. `cd ems-frontend && npm run build`.
2. `aws s3 sync dist/ s3://ems-frontend --delete`.
3. CloudFront avec *custom error response* 403/404 → `/index.html` (fallback SPA).
4. Invalidation : `aws cloudfront create-invalidation --distribution-id <id> --paths "/*"`.
