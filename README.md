# Guigno-Map 🎁

Système de gestion de la collecte de denrées pour **Le Relais de Mascouche**.

## 🌟 Fonctionnalités

- 🗺️ **Cartes interactives** avec géolocalisation complète des rues
  - Centrage automatique sur Mascouche
  - Couleurs par statut (rouge/jaune/vert)
  - Rues non assignées en pointillés
  - Cache intelligent avec rechargement automatique
  - **Couverture maximale** : toutes les voies nommées (sauf autoroutes)
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
- Système de cache auto-actualisant
- **Couverture complète** : toutes les rues, allées, impasses, voies d'accès

### Pour les Bénévoles
- Tournée assignée
- Ajout de notes par adresse
- Mise à jour du statut des rues
- Suivi en temps réel
- Carte centrée automatiquement sur la zone de travail
- Interface fluide avec rechargement intelligent des données
- **Visibilité totale** des voies de collecte (y compris voies privées)

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

### Cache OSM Révolutionnaire
- **Couverture maximale** : toutes les voies nommées de Mascouche
- **Exclusion ciblée** : seulement les autoroutes (motorway/motorway_link)
- **Inclusion totale** : rues principales, résidentielles, voies d'accès, impasses, allées, voies privées
- Cache Streamlit sensible aux modifications de fichier
- Rechargement automatique sans intervention manuelle
- Extraction robuste des coordonnées (geometry prioritaire, nodes en fallback)
- Requête Overpass optimisée avec regex négative avancée
- Gestion d'erreurs complète pour éviter les crashes

### Couverture des voies
- 🛣️ **Routes principales** : trunk, primary, secondary, tertiary
- 🏘️ **Voies résidentielles** : residential, living_street, unclassified
- 🚗 **Voies d'accès** : service, road, access
- 🏠 **Voies privées** : private roads, allées privées
- 🔚 **Impasses** : cul-de-sacs, dead ends
- 🚫 **Exclusions** : autoroutes uniquement

### Architecture technique
- **Frontend** : Streamlit avec cache intelligent à double sécurité
- **Géolocalisation** : API Overpass OSM avec requête révolutionnaire
- **Données** : SQLite + cache JSON optimisé pour performance maximale
- **Couverture** : Système d'inclusion maximale (tout sauf autoroutes)
- **Performance** : Cache à plusieurs niveaux avec auto-invalidation

## 📝 Support

Développé pour **Le Relais de Mascouche** - Collecte de denrées 2025

---
*Version 3.0 - Couverture maximale OSM et système révolutionnaire*
