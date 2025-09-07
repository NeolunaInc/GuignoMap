# Guigno-Map 🎁

Système de gestion de la collecte de denrées pour **Le Relais de Mascouche**.

## 🌟 Fonctionnalités

- 🗺️ **Cartes interactives** avec géolocalisation des rues
  - Centrage automatique sur Mascouche
  - Couleurs par statut (rouge/jaune/vert)
  - Rues non assignées en pointillés
- 👥 **Gestion d'équipes** avec authentification
- 📍 **Suivi par adresse** avec notes détaillées
- 📊 **Tableaux de bord** en temps réel
- 📥 **Export CSV** des données et rapports
- 🎨 **Interface moderne** avec thème personnalisé

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
- Mise à jour des données OSM
- Visualisation claire des statuts avec légende interactive

### Pour les Bénévoles
- Tournée assignée
- Ajout de notes par adresse
- Mise à jour du statut des rues
- Suivi en temps réel
- Carte centrée automatiquement sur la zone de travail

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

### Cache OSM
- Géométries des rues mises en cache
- Rafraîchissement manuel possible
- Fallback sur données de test

## 📝 Support

Développé pour **Le Relais de Mascouche** - Collecte de denrées 2025

---
*Version 2.2 - Interface améliorée avec centrage automatique et légende interactive*
