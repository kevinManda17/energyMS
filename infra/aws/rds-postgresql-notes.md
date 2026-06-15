# RDS PostgreSQL

1. Créer une instance RDS PostgreSQL 16 (`db.t3.micro` pour démarrer).
2. Réseau : même VPC que le backend ; Security Group autorisant le port `5432`
   uniquement depuis le SG du backend (EC2/ECS).
3. Créer la base `ems_db` et l'utilisateur `ems_user`.
4. Construire l'URL :
   ```
   DATABASE_URL=postgresql://ems_user:<password>@<endpoint>.rds.amazonaws.com:5432/ems_db
   ```
5. Activer les sauvegardes automatiques + Multi-AZ en production.
6. Migrer : `python manage.py migrate` (au démarrage du conteneur backend).
