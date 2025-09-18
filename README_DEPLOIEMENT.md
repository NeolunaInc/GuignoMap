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

---

*GuignoMap v4.1 - Template Multi-Villes*