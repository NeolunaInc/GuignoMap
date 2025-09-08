# GuignoMap - Système de gestion pour la Guignolée 2025 🎄

Une application web moderne conçue spécialement pour optimiser la collecte de dons lors de la Guignolée 2025 à Mascouche.

## ✨ Nouvelles fonctionnalités v3.0

### 🎄 Interface festive
- **Page d'accueil moderne** avec compte à rebours vers Noël
- **En-tête festif** aux couleurs de la Guignolée 2025
- **Carte de Noël thématique** avec icônes festives

### 📱 Optimisations mobiles
- **Interface responsive** optimisée pour tous les appareils
- **Navigation tactile** adaptée aux smartphones
- **Contrôles de carte** optimisés pour mobile

### 🏆 Système de motivation
- **Badges d'équipe** : Débutants, Actifs, Champions, Légendes
- **Notifications temps réel** pour les accomplissements
- **Tableaux de bord interactifs** avec graphiques Plotly

### 📊 Centre d'export avancé
- **Export Excel professionnel** avec formatage automatique
- **Génération de listes SMS** pour la communication d'équipe
- **Export PDF** (préparation)
- **Rapports détaillés** par équipe et secteur

### 🗺️ Améliorations cartographiques
- **Choix de fonds de carte** : OpenStreetMap France, CARTO Voyager, Esri
- **Zoom optimisé** centré sur Mascouche
- **Zone d'affichage agrandie** : 90% de l'écran sur PC
- **Gestion d'erreur robuste** : secrets.toml optionnel
- **Visibilité améliorée** des rues avec lignes plus épaisses
- **Récupération complète** de toutes les rues via OSM

### 👥 Gestion moderne
- **Terminologie unifiée** : "gestionnaire" au lieu de "superviseur"
- **Navigation sidebar** moderne et intuitive
- **Interface bénévole restreinte** aux rues assignées seulement
- **Authentification simplifiée** avec cartes de connexion

## 🚀 Installation et utilisation

### Prérequis
- Python 3.8+
- Accès internet pour OSM et les tuiles de carte

### Installation
```bash
git clone https://github.com/votre-repo/GuignoMap.git
cd GuignoMap
pip install -r requirements.txt
```

### Lancement
```bash
cd guignomap
streamlit run app.py
```

## 📦 Dépendances principales

- **streamlit** : Interface web moderne
- **folium** : Cartes interactives
- **pandas** : Manipulation des données
- **overpy** : API OpenStreetMap
- **plotly** : Graphiques interactifs
- **xlsxwriter** : Export Excel professionnel

## 🎯 Fonctionnalités principales

### Pour les bénévoles
- 🗺️ **Carte interactive** avec leurs rues assignées uniquement
- ✅ **Système de validation** rue par rue avec notes
- 🏆 **Badges de progression** et encouragements
- � **Interface mobile** optimisée

### Pour les gestionnaires
- 📊 **Tableau de bord complet** avec KPIs temps réel
- �️ **Vue d'ensemble** de toutes les équipes
- 📈 **Graphiques de progression** par Plotly
- � **Centre d'export** avec formats multiples
- 👥 **Gestion des équipes** et assignation
- � **Notifications** d'activité

### Données et exports
- 📝 **Base de données SQLite** intégrée
- 📊 **Export Excel** avec formatage professionnel
- 📱 **Listes SMS** pour communication
- 📄 **Rapports PDF** (en développement)
source .venv/bin/activate

## 🗃️ Structure du projet

```
GuignoMap/
├── guignomap/
│   ├── app.py              # Application principale Streamlit
│   ├── db.py               # Gestion base de données
│   ├── osm.py              # Interface OpenStreetMap
│   ├── guigno_map.db       # Base de données SQLite
│   ├── osm_cache.json      # Cache des données OSM
│   ├── streets_mascouche.csv # Données des rues
│   └── assets/
│       ├── banner.png      # Bannière Guignolée
│       ├── logo.png        # Logo officiel
│       └── styles.css      # Styles personnalisés
├── requirements.txt        # Dépendances Python
└── README.md              # Documentation
```

## 🎄 Thème Guignolée 2025

L'application adopte une identité visuelle festive pour l'édition 2025 :
- **Couleurs** : Rouge festif (#dc3545), vert sapin, or
- **Typographie** : Poppins pour une lecture moderne
- **Icônes** : Thème de Noël et solidarité
- **Animations** : Compte à rebours dynamique vers Noël

## � Statistiques temps réel

Le système suit automatiquement :
- Progression globale de la collecte
- Performance par équipe et bénévole
- Couverture géographique
- Tendances et objectifs

## 🔐 Sécurité et accès

- **Authentification** par nom d'équipe
- **Restriction d'accès** : bénévoles limités à leurs rues
- **Données locales** : pas de transmission externe
- **Sauvegarde automatique** des progressions

## 🤝 Contribution

GuignoMap est développé pour la Guignolée de Mascouche. Pour toute suggestion ou amélioration, contactez l'équipe organisatrice.

---

**Joyeuses Fêtes et bonne Guignolée 2025 ! 🎄🎁**
2. **Consultez votre liste** de rues assignées
3. **Commencez une rue** :
   - Sélectionnez la rue dans la liste
   - Changez le statut de "À faire" à "En cours"
4. **Pendant la collecte** :
   - Ajoutez des notes pour les adresses spéciales
   - Ex: "145 - Famille absente, denrées déposées"
5. **Terminez la rue** :
   - Une fois la rue complète, changez le statut à "Terminée"
6. **Passez à la rue suivante**

### 🆘 Que faire si...

#### ❓ **Je ne vois pas mes rues**
- Vérifiez que vous êtes connecté comme bénévole
- Demandez au superviseur si des rues vous ont été assignées

#### ❓ **Je ne peux pas me connecter**
- Vérifiez votre code d'équipe et mot de passe
- Contactez le superviseur pour confirmation

#### ❓ **La carte ne s'affiche pas**
- Actualisez la page (F5)
- Le superviseur peut reconstruire les données dans l'onglet Tech

#### ❓ **Je veux voir toute la ville**
- Seuls les superviseurs voient toute la carte
- Les bénévoles ne voient que leurs rues assignées

### 💡 Conseils pratiques

#### Pour les **superviseurs** :
- Créez les équipes AVANT d'assigner des rues
- Assignez des secteurs logiques (ex: même quartier)
- Consultez régulièrement l'onglet "Vue d'ensemble" pour le suivi
- Exportez les données à la fin pour les rapports

#### Pour les **bénévoles** :
- Changez le statut dès que vous commencez une rue
- Ajoutez des notes pour les situations particulières
- N'oubliez pas de marquer "Terminée" quand c'est fini
- Utilisez l'auto-refresh pour voir les mises à jour des autres équipes

### 🎨 Interface rapide
- **Menu gauche** : Navigation principale
- **Carte centrale** : Vue géographique avec couleurs
- **Légende en bas à droite** : Explication des couleurs et statistiques
- **Auto-refresh** : Active le rafraîchissement automatique toutes les 15 secondes

## 🔐 Connexion

### Superviseur
- **Portail** : 🎯 Superviseur
- **Mot de passe** : `admin123`
- **Fonctions** : Gestion complète + opérations techniques

### Bénévoles
- **Portail** : 👥 Bénévole
- **Identifiants** : Créés par le superviseur

## 📁 Structure du projet

```
GuignoMap/
├── guignomap/
│   ├── app.py              # Application principale
│   ├── db.py               # Gestion base de données robuste
│   ├── osm.py              # Intégration OpenStreetMap + adresses
│   ├── guigno_map.db       # Base SQLite
│   ├── osm_cache.json      # Cache géométries
│   ├── osm_addresses.json  # Cache adresses OSM
│   └── assets/
│       ├── styles.css      # Styles personnalisés
│       ├── logo.png        # Logo du Relais
│       └── banner.png      # Bannière (optionnel)
├── .streamlit/
│   └── config.toml         # Configuration Streamlit
├── requirements.txt        # Dépendances Python
└── README.md              # Documentation
```

## 🛠️ Technologies

- **Frontend** : Streamlit + CSS personnalisé
- **Backend** : Python + SQLite avec gestion d'erreurs
- **Cartes** : Folium + OpenStreetMap + API Overpass
- **Données** : Pandas + Overpy avec validation robuste

## 📊 Fonctionnalités détaillées

### Pour les Superviseurs
- Vue d'ensemble avec carte complète de Mascouche
- Gestion des équipes avec création/suppression
- Assignation intelligente des rues
- Export des rapports (rues + notes)
- **Onglet Tech** protégé par PIN pour :
  - Reconstruction du cache géométrique OSM
  - Import/mise à jour des adresses depuis OSM
  - Gestion d'erreurs avancée avec fallback
- Visualisation complète : autoroutes, rues principales, voies privées
- Statistiques en temps réel avec compteurs dynamiques

### Pour les Bénévoles
- Interface dédiée à leur tournée assignée
- Ajout de notes par adresse civique
- Mise à jour du statut des rues (à faire → en cours → terminée)
- Consultation des notes existantes
- Carte centrée sur leur zone de travail
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

### Légende de la carte améliorée
- 🟢 **Vert** : Rues terminées
- � **Orange** : Rues en cours
- 🔴 **Rouge** : Rues à faire
- **Lignes pleines** : Rues assignées à une équipe
- **Lignes pointillées** : Rues non assignées
- **Compteurs dynamiques** : Total, assignées, non assignées
- **Marqueur centre-ville** : Point de référence Mascouche

## 🚧 Développement

### Base de données renforcée
- Tables : `streets`, `teams`, `notes`, `activity_log`, `addresses`
- Import automatique depuis OpenStreetMap avec validation
- Gestion d'erreurs et création automatique des rues manquantes
- Données de test intégrées et fallback robuste

### Système OSM révolutionnaire v3.1
- **Couverture maximale** : TOUTES les voies nommées + autoroutes (ref)
- **Requête optimisée** : `highway+name OU highway+ref`
- **Cache multi-niveaux** : géométries + adresses OSM
- **Fallback étendu** : 19 voies principales de Mascouche
- **Gestion d'erreurs** : validation, retry, récupération automatique
- **Import adresses** : numéros civiques avec tri intelligent
- **Performance** : cache Streamlit sensible aux modifications

### Couverture des voies complète
- 🛣️ **Autoroutes** : A-25, A-640 (via ref)
- 🏘️ **Voies principales** : Montée Masson, Chemin Sainte-Marie
- 🚗 **Voies résidentielles** : toutes les rues nommées
- 🏠 **Voies d'accès** : service, private roads
- 🔚 **Impasses et allées** : couverture totale
- ✅ **Inclusions** : TOUT sauf limitation technique OSM

### Améliorations critiques v3.1
- **🐛 Fix create_map()** : Gestion robuste des colonnes DataFrame
- **🔧 Fix build_addresses_cache()** : Validation types et tri intelligent  
- **🛡️ Fix import_addresses_from_cache()** : Création automatique des rues
- **⚡ Fix list_streets()** : COALESCE pour éviter les NULL
- **🎯 UI améliorée** : Limites géographiques et zoom adaptatif
- **📊 Statistiques** : Compteurs en temps réel dans la légende

### Architecture technique
- **Frontend** : Streamlit avec gestion d'erreur globale
- **Géolocalisation** : API Overpass OSM avec requête universelle
- **Données** : SQLite + cache JSON double (géo + adresses)
- **Couverture** : Système d'inclusion universelle (name + ref)
- **Robustesse** : Fallback à tous les niveaux avec validation

## 📝 Changelog v3.3

### 🎄 Thème Guignolée festif
- **Header moderne** : Design spécial Guignolée 2025 avec dégradé rouge/vert
- **Animations** : Flocons de neige CSS pour ambiance festive
- **Branding** : "🎅 GUIGNOLÉE 2025 🎁" avec police Manrope
- **Stats temps réel** : Progression visible directement dans le header
- **Support logo** : Détection automatique du logo Guignolée

## 📝 Changelog v3.2

### 🗺️ Améliorations cartographiques majeures
- **Fonds multiples** : OSM France (détaillé), CARTO Voyager (moderne), Esri WorldStreetMap (professionnel)
- **Sélecteur de couches** : Contrôle dynamique pour changer de fond à la volée
- **Zoom optimisé** : zoom_start=13 pour meilleur cadrage de Mascouche
- **Performances** : prefer_canvas=True pour rendu fluide + contrôles complets
- **Visibilité** : weight 7/5 et opacity 0.9/0.7 pour meilleure lisibilité
- **Navigation** : zoom_control et scrollWheelZoom activés

### 🎯 Interface utilisateur
- **Terminologie** : "Code" → "Identifiant", "Nom" → "Équipe" pour clarté
- **UX** : Amélioration compréhension des champs par les utilisateurs

## 📝 Changelog v3.1

### 🔧 Corrections critiques
- **create_map()** : Gestion robuste colonnes pandas + limites géographiques
- **build_addresses_cache()** : Tri numérique intelligent + gestion d'erreurs
- **import_addresses_from_cache()** : Validation + création automatique rues
- **list_streets()** : COALESCE pour colonnes NULL + structure garantie
- **Requête OSM** : Inclusion autoroutes via ref + couverture maximale

### ✨ Nouvelles fonctionnalités  
- **Carte centrée Mascouche** : Bounds géographiques + zoom adaptatif
- **Légende avancée** : Statistiques temps réel + compteurs dynamiques
- **Marqueur centre-ville** : Point de référence visuel
- **Fallback étendu** : 19 voies principales + autoroutes
- **Gestion d'erreurs** : Messages informatifs + récupération automatique

## 📝 Support

Développé pour **Le Relais de Mascouche** - Collecte de denrées 2025

---
*Version 3.3 - Thème Guignolée festif + header moderne*
