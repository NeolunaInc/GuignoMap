# GuignoMap - Système de gestion pour la Guignolée 2025 🎄

Une application web moderne conçue spécialement pour optimiser la collecte de dons lors de la Guignolée 2025 à Mascouche.

## 📋 Table des matières

- [🎯 Vue d'ensemble](#-vue-densemble)
- [✨ Fonctionnalités principales](#-fonctionnalités-principales)
- [🚀 Installation et configuration](#-installation-et-configuration)
- [💻 Commandes pratiques](#-commandes-pratiques)
- [📊 Structure du projet](#-structure-du-projet)
- [🔧 Technologies et dépendances](#-technologies-et-dépendances)
- [🎨 Interfaces utilisateur](#-interfaces-utilisateur)
- [🛡️ Sécurité et robustesse](#️-sécurité-et-robustesse)
- [📈 Exports et rapports](#-exports-et-rapports)
- [🔄 Historique des versions](#-historique-des-versions)

## 🎯 Vue d'ensemble

GuignoMap est une application web complète développée avec Streamlit pour gérer la collecte de dons de la Guignolée annuelle de Mascouche. L'application offre une interface moderne et intuitive pour :

- **Gestion des équipes bénévoles** : Création, authentification et suivi des équipes
- **Assignation des rues** : Attribution intelligente des secteurs aux équipes
- **Suivi en temps réel** : Mise à jour des statuts de collecte (À faire → En cours → Terminée)
- **Cartographie interactive** : Visualisation des rues avec Folium et OpenStreetMap
- **Exports professionnels** : Génération de rapports Excel, CSV et PDF
- **Système de backup automatique** : Sauvegarde sécurisée des données critiques

## ✨ Fonctionnalités principales

### 👔 Interface Gestionnaire/Superviseur
- **Assignations par secteur** : Sélection secteur + équipe et assignation en bloc
- **Compteur rues non assignées** : Vue en temps réel des rues sans équipe
- **Export CSV assignations** : Colonnes secteur, rue, équipe, statut
- **Gestion d'erreur gracieuse** : Masquage des fonctionnalités indisponibles
- **Notifications toast** : Confirmations visuelles des actions

### 🎅 Interface Bénévole "Mes rues"
- **Vue filtrée par équipe** : Seulement les rues assignées à l'équipe connectée
- **Boutons de statut** : "En cours" et "Terminée" avec mise à jour immédiate
- **Gestion des notes** : Ajout/affichage des notes par adresse spécifique
- **Statistiques d'équipe** : Métriques de progression en temps réel
- **Journal d'activité** : Historique des actions de l'équipe

### 🗺️ Cartographie interactive
- **Carte centrée sur Mascouche** : Zoom optimisé et positionnement précis
- **Fonds de carte multiples** : OpenStreetMap France, CARTO Voyager, Esri
- **Légende persistante** : États visuels des rues (Terminée 🟢, En cours 🟡, À faire 🔴)
- **Récupération complète des rues** : Via API OpenStreetMap (OSM)
- **Visibilité améliorée** : Lignes épaisses pour une meilleure lisibilité

### 📊 Tableaux de bord
- **Statistiques temps réel** : Compteurs d'équipes, rues assignées/non assignées
- **Graphiques interactifs** : Plotly pour visualiser la progression
- **Badges de motivation** : Débutants, Actifs, Champions, Légends
- **Tableaux de progression** : Par équipe et secteur

## 🚀 Installation et configuration

### Prérequis système
- **Python** : 3.13.6 (recommandé)
- **OS** : Windows 10/11, macOS, Linux
- **RAM** : 4GB minimum
- **Stockage** : 500MB pour l'application + données

### Installation automatique
```bash
# Cloner le dépôt
git clone https://github.com/NeolunaInc/GuignoMap.git
cd GuignoMap

# Installation des dépendances
pip install -r requirements.txt
```

### Configuration manuelle (alternative)
```bash
# Créer l'environnement virtuel
python -m venv .venv

# Activer l'environnement virtuel
# Windows :
.venv\Scripts\activate
# macOS/Linux :
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### Configuration Streamlit
Le fichier `.streamlit/config.toml` contient la configuration par défaut :
- Thème sombre avec couleurs du Relais
- Layout large optimisé pour les cartes
- Paramètres de performance adaptés

## 💻 Commandes pratiques

### Gestion de l'environnement virtuel
```bash
# Activer l'environnement virtuel (Windows)
.venv\Scripts\activate

# Activer l'environnement virtuel (PowerShell)
& ".venv\Scripts\Activate.ps1"

# Activer l'environnement virtuel (macOS/Linux)
source .venv/bin/activate

# Désactiver l'environnement virtuel
deactivate
```

### Lancement de l'application
```bash
# Démarrage standard
streamlit run guignomap/app.py

# Démarrage en mode headless (serveur)
streamlit run guignomap/app.py --server.headless true --server.port 8501

# Démarrage avec configuration personnalisée
streamlit run guignomap/app.py --server.address 0.0.0.0 --server.port 8501
```

### Commandes Git essentielles
```bash
# Vérifier l'état du dépôt
git status

# Ajouter tous les changements
git add .

# Commiter les changements
git commit -m "Description des modifications"

# Pousser vers le dépôt distant
git push origin main

# Créer une nouvelle branche
git checkout -b feature/nouvelle-fonctionnalite

# Fusionner une branche
git checkout main
git merge feature/nouvelle-fonctionnalite

# Annuler les derniers changements
git reset --hard HEAD~1

# Voir l'historique des commits
git log --oneline -10
```

### Maintenance et débogage
```bash
# Vérifier la syntaxe Python
python -m py_compile guignomap/*.py

# Compiler tous les fichiers Python
python -m compileall .

# Tester l'importation des modules
python -c "import guignomap.app; print('Import réussi')"

# Vérifier les dépendances
pip check

# Mettre à jour les dépendances
pip install --upgrade -r requirements.txt
```

### Gestion des backups
```bash
# Créer un backup manuel (via l'interface)
# Accéder à l'onglet "Paramètres" > "Gestion des backups"

# Lister les backups disponibles
# Interface web : onglet "Paramètres" > "Télécharger backup"

# Nettoyer les anciens backups
# Automatique : conservation des 7 derniers jours
```

## 📊 Structure du projet

```
GuignoMap/
├── .streamlit/              # Configuration Streamlit
│   ├── config.toml         # Configuration thème et layout
│   └── secrets.toml        # Clés API et secrets (optionnel)
├── .vscode/                # Configuration VS Code
│   ├── settings.json       # Paramètres Pylance/Python
│   └── tasks.json          # Tâches de build/débug
├── guignomap/              # Code source principal
│   ├── __init__.py         # Initialisation package
│   ├── app.py              # Application Streamlit principale
│   ├── db.py               # Gestion base de données SQLite
│   ├── backup.py           # Système de sauvegarde automatique
│   ├── osm.py              # Intégration OpenStreetMap
│   ├── validators.py       # Validation des entrées utilisateur
│   ├── reports.py          # Génération de rapports
│   ├── guigno_map.db       # Base de données SQLite
│   ├── assets/             # Ressources statiques
│   │   ├── styles.css      # Feuilles de style CSS
│   │   ├── banner.png      # Bannière Guignolée
│   │   ├── logo.png        # Logo Relais
│   │   └── guignolee.png   # Icône Guignolée
│   └── logs/               # Journaux d'activité
│       └── activity.log    # Historique des actions
├── tools/                  # Outils de développement
├── typings/                # Définitions de types
├── .gitignore              # Fichiers à ignorer par Git
├── requirements.txt        # Dépendances Python
├── lancer_guignomap.ps1    # Script de lancement Windows
└── README.md               # Cette documentation
```

## 🔧 Technologies et dépendances

### Environnement de développement
- **Python** : 3.13.6
- **Gestionnaire de paquets** : pip 25.2
- **Environnement virtuel** : venv (inclus)

### Dépendances principales
```
streamlit==1.49.1          # Framework web principal
folium==0.20.0             # Cartes interactives
streamlit-folium==0.25.1   # Intégration Folium-Streamlit
pandas==2.3.2              # Manipulation de données
plotly==6.3.0              # Graphiques interactifs
bcrypt==4.3.0              # Hachage sécurisé des mots de passe
pillow==11.3.0             # Traitement d'images
requests==2.32.5           # Requêtes HTTP
```

### Dépendances complètes (pip freeze)
```
altair==5.5.0
attrs==25.3.0
bcrypt==4.3.0
blinker==1.9.0
branca==0.8.1
cachetools==6.2.0
certifi==2025.8.3
charset-normalizer==3.4.3
click==8.3.0
colorama==0.4.6
folium==0.20.0
gitdb==4.0.12
GitPython==3.1.45
idna==3.10
Jinja2==3.1.6
jsonschema==4.25.1
jsonschema-specifications==2025.9.1
MarkupSafe==3.0.2
narwhals==2.5.0
numpy==2.3.3
packaging==25.0
pandas==2.3.2
pillow==11.3.0
pip==25.2
plotly==6.3.0
protobuf==6.32.1
pyarrow==21.0.0
pydeck==0.9.1
python-dateutil==2.9.0.post0
pytz==2025.2
referencing==0.36.2
requests==2.32.5
rpds-py==0.27.1
six==1.17.0
smmap==5.0.2
streamlit==1.49.1
streamlit-folium==0.25.1
tenacity==9.1.2
toml==0.10.2
tornado==6.5.2
typing_extensions==4.15.0
tzdata==2025.2
urllib3==2.5.0
watchdog==6.0.0
xyzservices==2025.4.0
```

## 🎨 Interfaces utilisateur

### Page d'accueil
- **Compte à rebours Noël** : Jours restants avant la Guignolée
- **Carte festive** : Icônes thématiques et couleurs de saison
- **Navigation intuitive** : Accès rapide aux différentes sections

### Interface Gestionnaire
- **Tableau des assignations** : Vue d'ensemble secteur/rue/équipe/statut
- **Sélecteurs dynamiques** : Filtrage par secteur et équipe
- **Actions groupées** : Assignation en bloc des rues
- **Exports spécialisés** : CSV pour la gestion opérationnelle

### Interface Bénévole
- **Vue personnalisée** : Seulement les rues de l'équipe connectée
- **Actions simplifiées** : Boutons "En cours" et "Terminée"
- **Notes contextuelles** : Commentaires par adresse
- **Suivi personnel** : Progression individuelle de l'équipe

### Interface Superviseur (hérité)
- **Vue d'ensemble** : Tous les secteurs et équipes
- **Gestion centralisée** : Création et modification des équipes
- **Statistiques globales** : Métriques de toute la collecte

## 🛡️ Sécurité et robustesse

### Authentification
- **Hachage bcrypt** : Mots de passe sécurisés avec salage
- **Migration automatique** : Anciens mots de passe SHA256 convertis
- **Sessions sécurisées** : Gestion d'état Streamlit
- **Validation stricte** : Entrées utilisateur nettoyées

### Protection des données
- **Injection SQL prévenue** : Requêtes paramétrées
- **XSS évité** : Sanitisation HTML automatique
- **Validation d'entrée** : Contrôles stricts sur tous les formulaires

### Sauvegarde automatique
- **Backup avant écritures** : Toutes opérations critiques sauvegardées
- **Format ZIP horodaté** : Archives compressées avec timestamp
- **Rotation automatique** : Conservation 7 jours glissants
- **Récupération facile** : Interface de téléchargement

### Robustesse applicative
- **Gestion d'erreur** : Application ne crash jamais
- **Dégradation gracieuse** : Fonctionnalités indisponibles masquées
- **Logging complet** : Base de données + fichiers texte
- **Validation continue** : Données vérifiées à chaque étape

## 📈 Exports et rapports

### Formats supportés
- **Excel professionnel** : Formatage automatique, couleurs, mise en page
- **CSV spécialisé** : Données brutes pour traitement automatisé
- **PDF** : Préparation pour rapports imprimables
- **Listes SMS** : Extraction de contacts pour communication

### Exports spécialisés
- **Assignations CSV** : Secteur, rue, équipe, statut pour gestion
- **Rapports d'équipe** : Statistiques individuelles et collectives
- **Historique d'activité** : Journal complet des actions
- **Données cartographiques** : Export des géométries OSM

### Interface unifiée
- **Accès centralisé** : Onglet "Export" pour tous les formats
- **Prévisualisation** : Aperçu avant téléchargement
- **Nommage automatique** : Timestamps et descriptions claires

## 🔄 Historique des versions

### v4.1 - Interface moderne et robustesse (2025)
- ✅ Interface gestionnaire avec assignations par secteur
- ✅ Interface bénévole "Mes rues" filtrée
- ✅ Système de backup automatique complet
- ✅ Migration sécurité bcrypt + validation stricte
- ✅ Cartographie améliorée avec légendes persistantes
- ✅ Exports professionnels Excel/CSV
- ✅ Interface responsive mobile
- ✅ Thème festif et motivation par badges

### v4.0 - Sécurité renforcée (2024)
- ✅ Migration mots de passe bcrypt
- ✅ Système backup automatique
- ✅ Validation d'entrée complète
- ✅ Sanitisation données utilisateur

### v3.0 - Interface festive (2024)
- ✅ Page d'accueil thématique Noël
- ✅ Optimisations mobiles complètes
- ✅ Système de motivation par badges
- ✅ Centre export avancé

### v2.0 - Fonctionnalités cartographiques (2024)
- ✅ Cartes interactives Folium
- ✅ Récupération rues OSM complète
- ✅ Fonds de carte multiples
- ✅ Légende visuelle persistante

### v1.0 - Base fonctionnelle (2024)
- ✅ Authentification équipes
- ✅ Gestion base de données
- ✅ Interface de base Streamlit
- ✅ Structure applicative initiale

---

## 🎄 Support et contribution

Pour toute question ou suggestion d'amélioration :
- **Documentation complète** : Ce README et fichiers d'aide
- **Code source commenté** : Fonctions documentées en français
- **Structure modulaire** : Séparation claire des responsabilités
- **Tests validés** : Compilation et importation vérifiés

**GuignoMap - Ensemble pour une Guignolée réussie ! 🎅**