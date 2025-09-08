# Guigno-Map 🎁

Système de gestion de la collecte de denrées pour **Le Relais de Mascouche**.

## 🌟 Fonctionnalités

- 🗺️ **Cartes interactives** avec géolocalisation complète des rues
  - **Fonds de carte multiples** : OSM France, CARTO Voyager, Esri WorldStreetMap
  - **Sélecteur de couches** pour changer de fond à la volée
  - **Zoom optimisé** (13) avec contrôles molette et boutons
  - **Rendu Canvas** pour performances améliorées
  - **Visibilité renforcée** : lignes plus épaisses et opaques
  - Centrage automatique sur Mascouche avec limites géographiques
  - Couleurs par statut (rouge/orange/vert)
  - Affichage différencié : lignes pleines (assignées) / pointillées (non assignées)
  - Cache intelligent avec rechargement automatique
  - **Couverture maximale** : TOUTES les voies nommées + autoroutes (ref)
  - Marqueur centre-ville et légende statistique avancée
- 👥 **Gestion d'équipes** avec authentification
- 📍 **Suivi par adresse** avec notes détaillées et import OSM
- 📊 **Tableaux de bord** en temps réel avec métriques étendues
- 📥 **Export CSV** des données et rapports complets
- 🎨 **Interface moderne** avec thème personnalisé du Relais
- 🔄 **Système de cache OSM** ultra-robuste avec fallback étendu
- ⚠️ **Gestion d'erreurs** renforcée avec validation de données

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

## 📖 Guide pour débutants - Comment utiliser Guigno-Map

### 🎯 Qu'est-ce que Guigno-Map ?
Guigno-Map est un système qui aide **Le Relais de Mascouche** à organiser la collecte de denrées alimentaires dans toute la ville. L'application affiche une carte interactive de Mascouche avec toutes les rues colorées selon leur statut de collecte.

### 🗺️ Comprendre la carte
- **🔴 Rouge** : Rues pas encore visitées (à faire)
- **🟠 Orange** : Collecte en cours sur cette rue
- **🟢 Vert** : Collecte terminée sur cette rue
- **Lignes pleines** : Rue assignée à une équipe
- **Lignes pointillées** : Rue pas encore assignée

### 👥 Les deux types d'utilisateurs

#### 🎯 **Superviseur** (Organisateur de la collecte)
**Comment se connecter :**
1. Cliquez sur "🎯 Superviseur" dans le menu gauche
2. Entrez le mot de passe : `admin123`

**Ce que vous pouvez faire :**
- **Voir toute la collecte** : Carte complète avec toutes les rues de Mascouche
- **Créer des équipes** : Onglet "👥 Équipes" → "Créer une équipe"
  - Donnez un code (ex: "EQUIPE1")
  - Un nom (ex: "Famille Tremblay") 
  - Un mot de passe pour l'équipe
- **Assigner des rues** : Onglet "🗺️ Assignation"
  - Choisissez une équipe
  - Sélectionnez les rues à leur donner
  - Cliquez "Assigner"
- **Voir les rapports** : Onglet "📥 Export" pour télécharger les données
- **Opérations techniques** : Onglet "🛠 Tech" (nécessite un PIN spécial)

#### 👥 **Bénévole** (Membre d'une équipe)
**Comment se connecter :**
1. Cliquez sur "👥 Bénévole" dans le menu gauche  
2. Entrez votre code d'équipe (donné par le superviseur)
3. Entrez votre mot de passe d'équipe

**Ce que vous pouvez faire :**
- **Voir vos rues** : Seules les rues assignées à votre équipe apparaissent
- **Changer le statut** : 
  - Sélectionnez une rue dans la liste
  - Choisissez le nouveau statut (à faire → en cours → terminée)
  - Cliquez "Mettre à jour le statut"
- **Ajouter des notes** :
  - Entrez un numéro civique (ex: "123")
  - Écrivez un commentaire (ex: "Pas de réponse, boîte pleine")
  - Cliquez "Ajouter la note"
- **Consulter les notes** : Voir toutes les notes de votre équipe

### 📱 Utilisation étape par étape pour les bénévoles

#### Jour de collecte :
1. **Connectez-vous** avec vos identifiants d'équipe
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
