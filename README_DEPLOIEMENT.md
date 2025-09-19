# Guide de Déploiement - GuignoMap

## Pré-requis

- **Python 3.11+** (recommandé)
- **pip** et **virtualenv**
- **Git** pour cloner le repository

## Lancement Local Rapide

```bash
# 1. Cloner et installer
git clone https://github.com/NeolunaInc/GuignoMap.git
cd GuignoMap

# 2. Créer l'environnement virtuel et installer les dépendances
python -m venv .venv
.venv\Scripts\activate  # Windows
# ou source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 3. Lancer l'application
streamlit run guignomap/app.py
```

L'application sera accessible sur `http://localhost:8501`

## Déploiement Streamlit Cloud

### Configuration Repository

1. **Repository** : Fork ou clone de `NeolunaInc/GuignoMap`
2. **Main file path** : `guignomap/app.py`
3. **Python version** : `3.11` (ou plus récent)
4. **Branch** : `main`

### Avantages 100% SQLite

- ✅ **Aucune variable secrète requise**
- ✅ **Base de données intégrée** (SQLite)
- ✅ **Déploiement simplifié** (un seul repository)
- ✅ **Pas de configuration externe**

### Limitations

- **Taille de DB recommandée** : < 10 MB
- **Données persistantes** : limitées à la durée de vie du container
- **Pas de backup automatique** (utiliser les exports CSV)

## Multi-Villes

### Préparer une nouvelle ville

Utilisez le script de setup pour créer une base de données dédiée :

```bash
python scripts/setup_nouvelle_ville.py "Nom De La Ville"
```

Exemple :
```bash
python scripts/setup_nouvelle_ville.py "Laval"
# Crée: data/laval.db
```

### Personnaliser les paramètres

Modifiez `guignomap/config_ville.py` pour ajuster :
- Nom de la ville
- Centre de la carte (latitude, longitude)
- Limites géographiques (bounds)
- Zoom par défaut

### Utiliser une DB spécifique

Pour utiliser une base de données d'une autre ville, copiez le fichier :
```bash
cp data/laval.db guignomap/guigno_map.db
```

## Structure du Projet

```
GuignoMap/
├── guignomap/           # Application principale
│   ├── app.py          # Point d'entrée Streamlit
│   ├── config_ville.py # Configuration ville
│   ├── database.py     # Couche base de données
│   └── guigno_map.db   # Base SQLite principale
├── scripts/            # Outils
│   └── setup_nouvelle_ville.py
├── data/              # Bases de données additionnelles
├── requirements.txt   # Dépendances Python
└── README_DEPLOIEMENT.md
```

## Support et Maintenance

- **Exports** : Utilisez la fonction d'export CSV pour sauvegarder
- **Sanity Check** : `python tools/quick_sanity.py`
- **Tests** : `python -m pytest`
- **Logs** : Consultez `guignomap/logs/activity.log`

## Troubleshooting

- **Port 8501 occupé** : `streamlit run guignomap/app.py --server.port 8502`
- **Erreur import** : Vérifier `.venv` activé et `pip install -r requirements.txt`
- **DB corrompue** : Supprimer `guignomap/guigno_map.db` (sera recréée)

## Déploiement Streamlit Cloud (Recommandé)

### 1. Préparer le Repository

1. **Fork** ce repository vers votre compte GitHub
2. **Cloner** votre fork localement
3. **Préparer la base de données** :
   ```bash
   # Utiliser la DB sample comme base
   cp guignomap/guigno_map.sample.db guignomap/guigno_map.db
   
   # Ou importer vos données
   python scripts/import_addresses.py votre_fichier.xlsx
   
   # Créer une nouvelle sample DB
   cp guignomap/guigno_map.db guignomap/guigno_map.sample.db
   ```

### 2. Configurer Streamlit Cloud

1. **Connecter** : Aller sur [share.streamlit.io](https://share.streamlit.io)
2. **Nouveau app** : 
   - Repository : `VotreCompte/GuignoMap`
   - Branch : `main`
   - Main file path : `guignomap/app.py`
3. **Variables d'environnement** (optionnel) :
   ```toml
   # Dans .streamlit/secrets.toml
   [general]
   ALLOW_BCRYPT_FALLBACK = true
   
   [app]
   CITY = "mascouche"
   MAP_DEFAULT_LAT = 45.748
   MAP_DEFAULT_LON = -73.600
   MAP_DEFAULT_ZOOM = 12
   
   # PIN technique pour admin (optionnel)
   TECH_PIN = "votre_pin_secret"
   ```

### 3. Base de Données pour Production

**Option A : Sample DB (Rapide)**
```bash
# Utiliser la DB exemple avec données de test
cp guignomap/guigno_map.sample.db guignomap/guigno_map.db
git add guignomap/guigno_map.db
git commit -m "feat: add production database"
git push
```

**Option B : Import Custom (Recommandé)**
```bash
# 1. Importer vos données d'adresses
python scripts/import_addresses.py vos_adresses.xlsx

# 2. Vérifier l'import
python scripts/verify_addresses.py

# 3. Créer snapshot de production
cp guignomap/guigno_map.db guigno_map_prod_$(date +%Y%m%d).db

# 4. Committer la DB de production
git add guignomap/guigno_map.db
git commit -m "feat: add production database with $(python -c 'from guignomap.database import stats_addresses; print(stats_addresses()["total"])') addresses"
git push
```

### 4. Avantages Streamlit Cloud

✅ **Déploiement automatique** : Push → Redéploiement  
✅ **HTTPS gratuit** : Certificat SSL automatique  
✅ **Domaine personnalisé** : Possible avec plan payant  
✅ **Monitoring** : Logs et métriques intégrés  
✅ **Scaling automatique** : Gestion de la charge  
✅ **SQLite intégré** : Aucune DB externe requise  

### 5. Limitations à Considérer

⚠️ **Persistance** : Les données SQLite peuvent être perdues lors des redéploiements  
⚠️ **Taille** : Repository limité à ~1GB  
⚠️ **Performance** : Limites CPU/RAM du plan gratuit  
⚠️ **Backup** : Utiliser les exports CSV réguliers  

### 6. Maintenance et Monitoring

```bash
# Export régulier des données
python scripts/export_all.py

# Vérification sanité
python tools/quick_sanity.py

# Tests complets
python -m pytest tests/ -v
```

**Recommandation** : Configurer un cron job pour les exports automatiques des données critiques.

---

*GuignoMap v4.2 - Streamlit Cloud Ready*