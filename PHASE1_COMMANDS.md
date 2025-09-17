# GuignoMap v5.0 - Commandes PowerShell PHASE 1
# Migration infrastructure vers prod Streamlit Cloud
# Windows PowerShell - Toutes les commandes prÀªtes À  exécuter

## 1. Configuration initiale de l'environnement

### Activer l'environnement virtuel existant
```powershell
cd c:\Users\nick\guignomap_clone\GuignoMap
.\.venv\Scripts\Activate.ps1
```

### Installer les nouvelles dépendances
```powershell
# Dependencies PostgreSQL + Auth + Storage
pip install --only-binary=all psycopg2-binary
pip install sqlalchemy==2.0.43 alembic==1.16.5 passlib[argon2]==1.7.4 boto3==1.34.144
```

## 2. Configuration Secrets Streamlit

### Éditer le fichier .streamlit\secrets.toml avec vos vraies valeurs :
```toml
[database]
url = "postgresql://user:password@host:5432/database_name"
pool_size = 5
max_overflow = 10

[storage]
s3_bucket = "votre-bucket-s3"
s3_region = "us-east-1"
s3_access_key = "votre-access-key"
s3_secret_key = "votre-secret-key"
```

## 3. Migration base de données

### Générer la première révision Alembic
```powershell
alembic revision --autogenerate -m "initial_schema"
```

### Appliquer les migrations À  PostgreSQL
```powershell
alembic upgrade head
```

### Migrer les données SQLite â†’ PostgreSQL
```powershell
python scripts\migrate_sqlite_to_postgres.py
```

## 4. Vérifications et tests

### Analyser les mots de passe existants
```powershell
python scripts\migrate_password_hashes.py analyze
```

### Générer un rapport détaillé de migration
```powershell
python scripts\migrate_password_hashes.py report
```

### Tester les fonctions de stockage
```powershell
python -c "from src.storage import get_storage_info; import json; print(json.dumps(get_storage_info(), indent=2, default=str))"
```

### Tester la connexion PostgreSQL
```powershell
python -c "from src.database.connection import test_connection; print('ðŸ”Œ Connexion PostgreSQL:', test_connection())"
```

## 5. Lancement de l'application

### Démarrer Streamlit avec la nouvelle configuration
```powershell
# Depuis le répertoire guignomap/
cd guignomap
..\\.venv\Scripts\python.exe -m streamlit run app.py
```

### Ou utiliser la tâche VS Code configurée
```powershell
# Via la palette de commandes VS Code:
# Tasks: Run Task > "GuignoMap: Run (Streamlit)"
```

## 6. Commandes de maintenance

### Backup manuel
```powershell
python -c "from src.storage import upload_backup; from pathlib import Path; upload_backup(Path('guignomap/guigno_map_backup.db'))"
```

### Lister les backups cloud
```powershell
python -c "from src.storage import list_backups; import json; print(json.dumps(list_backups(), indent=2, default=str))"
```

### Purger le cache OSM et forcer rechargement
```powershell
python -c "from src.storage import upload_osm_cache; upload_osm_cache({})"
```

## 7. Monitoring et diagnostics

### Vérifier l'état du stockage
```powershell
python -c "from src.storage import get_storage_info; print('Backend:', get_storage_info()['backend'])"
```

### Analyser les performances DB
```powershell
python -c "from src.database.connection import get_engine; print('Pool info:', get_engine().pool.status())"
```

## 8. Rollback d'urgence (si nécessaire)

### Revenir À  SQLite temporairement
```powershell
# 1. Modifier src/config.py pour retourner "sqlite:///guigno_map.db"
# 2. Relancer l'application
..\\.venv\Scripts\python.exe -m streamlit run app.py
```

### Restaurer un backup
```powershell
# Lister les backups disponibles
python -c "from src.storage import list_backups; [print(f'{i}: {b[\"filename\"]}') for i, b in enumerate(list_backups())]"

# Restaurer un backup spécifique (remplacer BACKUP_KEY)
python -c "from src.storage import download_backup; from pathlib import Path; download_backup('BACKUP_KEY', Path('guigno_map_restored.db'))"
```

## Notes importantes

1. **Politique de mot de passe** : Conservée À  min 4 caractères + confirmation (UI v4.1)
2. **Migration des hashes** : Automatique lors de la prochaine connexion réussie
3. **Stockage** : S3 si configuré, sinon fallback local automatique
4. **Base de données** : PostgreSQL en production, SQLite en dev/fallback
5. **Retry logic** : Intégrée pour toutes les opérations DB critiques

## Dépannage

### Si erreur PostgreSQL
```powershell
# Vérifier la connexion
python -c "from src.database.connection import test_connection; test_connection()"
```

### Si erreur S3
```powershell
# Vérifier la configuration
python -c "from src.storage import get_storage_info; print(get_storage_info())"
```

### Si erreur Alembic
```powershell
# Vérifier l'état des migrations
alembic current
alembic history
```

## Structure finale v5.0
```
GuignoMap/
â”œâ”€â”€ .streamlit/
â”‚   â””â”€â”€ secrets.toml              # Configuration centralisée
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ config.py                 # Accès aux secrets
â”‚   â”œâ”€â”€ auth/
â”‚   â”‚   â””â”€â”€ passwords.py          # Argon2 + bcrypt compat
â”‚   â”œâ”€â”€ database/
â”‚   â”‚   â”œâ”€â”€ connection.py         # PostgreSQL + retry
â”‚   â”‚   â”œâ”€â”€ models.py             # SQLAlchemy models
â”‚   â”‚   â””â”€â”€ migrations/           # Alembic migrations
â”‚   â””â”€â”€ storage/
â”‚       â”œâ”€â”€ __init__.py           # API unifiée
â”‚       â”œâ”€â”€ cloud.py              # Client S3
â”‚       â””â”€â”€ local.py              # Fallback local
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ migrate_sqlite_to_postgres.py
â”‚   â””â”€â”€ migrate_password_hashes.py
â””â”€â”€ guignomap/
    â””â”€â”€ app.py                    # Application Streamlit
```