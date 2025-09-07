# Guigno-Map 🎁

Système de gestion de la collecte de denrées pour **Le Relais de Mascouche**.

## 🌟 Fonctionnalités

- 🗺️ **Cartes interactives** avec géolocalisation des rues
  - Centrage automatique sur Mascouche
  - Couleurs par statut (rouge/jaune/vert)
  - Rues non assignées en pointillés
  - Cache intelligent avec rechargement automatique
- 👥 **Gestion d'équipes** avec authentification
- 📍 **Suivi par adresse** avec notes détaillées
- 📊 **Tableaux de bord** en temps réel
- 📥 **Export CSV** des données et rapports
- 🎨 **Interface moderne** avec thème personnalisé
- 🔄 **Système de cache OSM** robuste et auto-actualisant

## 🚀 Installation

### Prérequis
- Python 3.8+
- WSL Ubuntu (recommandé)

### Configuration
```bash
# Cloner le projet
git clone <votre-repo>
cd GuignoMap

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

## 🎯 Lancement

```bash
# Activer l'environnement virtuel
source .venv/bin/activate

# Lancer l'application
streamlit run guignomap/app.py
```

L'application sera accessible sur : `http://localhost:8501`

## 🔐 Connexion

### Superviseur
- **Portail** : 🎯 Superviseur
- **Mot de passe** : `admin123`

### Bénévoles
- **Portail** : 👥 Bénévole
- **Identifiants** : Créés par le superviseur

## 📁 Structure du projet

```
GuignoMap/
├── guignomap/
│   ├── app.py              # Application principale
│   ├── db.py               # Gestion base de données
│   ├── osm.py              # Intégration OpenStreetMap
│   └── assets/
│       ├── styles.css      # Styles personnalisés
│       └── logo.png        # Logo du Relais
├── .streamlit/
│   └── config.toml         # Configuration Streamlit
├── requirements.txt        # Dépendances Python
└── README.md              # Documentation
```

## 🛠️ Technologies

- **Frontend** : Streamlit + CSS personnalisé
- **Backend** : Python + SQLite
- **Cartes** : Folium + OpenStreetMap
- **Données** : Pandas + Overpy (API Overpass)

## 📊 Fonctionnalités détaillées

### Pour les Superviseurs
- Vue d'ensemble de la collecte
- Gestion des équipes
- Assignation des rues
- Export des rapports
- Mise à jour des données OSM avec cache intelligent
- Visualisation claire des statuts avec légende interactive
- Système de cache auto-actualisant (plus de "0 rues trouvées")

### Pour les Bénévoles
- Tournée assignée
- Ajout de notes par adresse
- Mise à jour du statut des rues
- Suivi en temps réel
- Carte centrée automatiquement sur la zone de travail
- Interface fluide avec rechargement intelligent des données

## 🎨 Thème visuel

Interface moderne aux couleurs du **Relais de Mascouche** :
- Rouge bordeaux (#8B0000)
- Or (#FFD700)
- Design responsive
- Animations fluides

### Légende de la carte
- 🟢 **Vert** : Rues terminées
- 🟡 **Jaune** : Rues en cours
- 🔴 **Rouge** : Rues à faire
- **Pointillés** : Rues non assignées à une équipe

## 🚧 Développement

### Base de données
- Tables : `streets`, `teams`, `notes`, `activity_log`
- Import automatique depuis OpenStreetMap
- Données de test intégrées

### Cache OSM Intelligent
- Géométries des rues mises en cache (`osm_cache.json`)
- Cache Streamlit sensible aux modifications de fichier
- Rechargement automatique sans intervention manuelle
- Extraction robuste des coordonnées (geometry prioritaire, nodes en fallback)
- Requête Overpass optimisée (trunk inclus, autoroutes exclues)
- Gestion d'erreurs avancée pour éviter les "NoneType" crashes

### Architecture technique
- **Frontend** : Streamlit avec cache intelligent
- **Géolocalisation** : API Overpass OSM avec extraction robuste
- **Données** : SQLite + cache JSON optimisé
- **Performance** : Système de cache à plusieurs niveaux

## 📝 Support

Développé pour **Le Relais de Mascouche** - Collecte de denrées 2025

---
*Version 2.3 - Système de cache OSM robuste et intelligence automatique*
