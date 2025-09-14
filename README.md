# GuignoMap - Système de gestion pour la Guignolée 2025 🎄

Une application web moderne conçue spécialement pour optimiser la collecte de dons lors de la Guignolée 2025 à Mascouche.

## ✨ Nouvelles fonctionnalités v4.1

### 👔 Interface Superviseur/Gestionnaire
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

### 🛡️ Sécurité et robustesse v4.1
- **Validation stricte** : Réutilisation des validators pour toutes les entrées
- **Backup automatique** : Décorateur auto_backup_before_critical sur toutes les écritures
- **Logging complet** : Journal d'activité en base de données ET fichier texte
- **Gestion d'erreur** : Dégradation gracieuse sans plantage de l'application

### 📊 Exports professionnels
- **Maintien des exports PDF/Excel** : Aucune modification des fonctionnalités existantes
- **Nouveau CSV assignations** : Export spécialisé pour la gestion des secteurs
- **Interface unifiée** : Tous les exports accessibles depuis l'onglet Export

## ✨ Fonctionnalités v4.0 (acquises)

### 🔒 Sécurité renforcée
- **Migration bcrypt** : Remplacement SHA256 par bcrypt avec salage automatique
- **Migration automatique** des anciens mots de passe
- **Validation d'entrées** : Protection contre injection SQL et XSS
- **Sanitisation complète** de toutes les données utilisateur

### 💾 Système de backup automatique
- **Backup automatique** avant toutes opérations critiques
- **Format ZIP** avec horodatage
- **Rotation automatique** : conservation 7 jours
- **Interface de gestion** des backups avec téléchargement

## ✨ Fonctionnalités v3.0 (acquises)

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

### 🗺️ Légende de la carte (persistante)
- **4 états visuels** :
  - 🟢 **Vert** : Rues terminées (collecte finie)
  - 🟡 **Jaune** : Rues en cours (équipe active)
  - 🔴 **Rouge plein** : Rues assignées à faire (équipe désignée)
  - 🔴 **Rouge pointillé** : Rues non assignées (aucune équipe)
- **Position fixe** : Bas-droite de la carte
- **Persistance garantie** : Reste visible au zoom/dézoom/déplacement
- **Style moderne** : Fond blanc, bordure, ombre portée

### ⚙️ Compatibilité et modernisation
- **Python 3.13.6** et versions récentes de Streamlit
- **Suppression de use_container_width** (déprécié) ➜ `width="stretch"`
- **Migration pandas Styler** : `applymap()` ➜ `map()` avec helper de compatibilité
- **Légende persistante** via Folium Elements (remplace l'ancien HTML/CSS)
- **Chemins multi-plateformes** avec pathlib
- **Gestion des erreurs robuste** : l'application ne crash jamais
- **Code moderne** : Nettoyage des anciens hacks et workarounds

### 🎨 Affichage des statuts
- **Codes internes** : `a_faire`, `en_cours`, `terminee` (base de données)
- **Affichage UI/exports** : "À faire", "En cours", "Terminée" (interface utilisateur)
- **Style visual** : Fond pastel + texte contrasté, uniquement sur la colonne "Statut"
- **Couleurs harmonisées** : 
  - 🟢 **Terminée** : Fond vert pâle (#E6F5EA)
  - 🟡 **En cours** : Fond jaune pâle (#FFF3CC)  
  - 🔴 **À faire** : Fond rose pâle (#FFE6EC)

### 🔧 Interface assignations
- **Sélecteur secteur** : Label clair "SECTEUR À ASSIGNER", aucun chevauchement
- **Tableau état** : Colonnes Rue / Secteur / Équipe / Statut avec libellés français
- **Style uniforme** : Rendu standard avec thème sombre (fond neutre, texte blanc)
- **Corrections UI** :
  - Suppression de l'overlay texte au-dessus du sélecteur secteur
  - Colonne 'Statut' : rendu uniforme (fond neutre / texte thème)

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

### Lancement (Windows)
```powershell
# Activer l'environnement virtuel
.\.venv\Scripts\Activate.ps1

# Lancer l'application
cd .\guignomap
streamlit run app.py
```

### Exports PDF/Excel
- **Boutons de téléchargement** : Disponibles dans l'onglet "📥 Export"
- **Emplacement recommandé** : `.\guignomap\exports` pour sauvegarde locale
- **Formats disponibles** : Excel (.xlsx), PDF (.pdf), CSV assignations

### Ouvrir le dernier export (PowerShell)
```powershell
$d = Join-Path $PSScriptRoot 'guignomap'
Set-Location $d
if (-not (Test-Path "..\exports")) { New-Item -ItemType Directory "..\exports" | Out-Null }
$f = Get-ChildItem "..\exports" -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
if ($f) { ii $f.FullName } else { ii "..\exports" }
```

## 📦 Dépendances principales

- **streamlit** : Interface web moderne
- **folium** : Cartes interactives
- **pandas** : Manipulation des données
- **overpy** : API OpenStreetMap
- **plotly** : Graphiques interactifs
- **xlsxwriter** : Export Excel professionnel
- **reportlab** : Génération PDF professionnelle
- **bcrypt** : Hachage sécurisé des mots de passe

### Sécurité/Robustesse
- **bcrypt** : Migration automatique des anciens hash SHA256 vers bcrypt avec salage
- **Backup automatique** : ZIP créé avant toute écriture critique
- **Validation inputs** : Protection SQL injection et XSS via module validators
- **Logging complet** : Journal d'activité en base de données et fichier

## 🔧 Notes techniques

### Compatibilité pandas 2.4+
L'application utilise un helper `style_map_compat()` pour gérer la transition de `Styler.applymap()` vers `Styler.map()` :
```python
def style_map_compat(df: pd.DataFrame, fn: Callable[[Any], str], subset: Any = None):
    """Helper de compatibilité pandas - applymap() vs map()"""
    styler = df.style
    if hasattr(styler, "map"):
        return styler.map(fn, subset=subset)  # Pandas 2.4+
    return getattr(styler, "applymap")(fn, subset=subset)  # Pandas < 2.4
```

### Environment virtuel (.venv)
- **Développement** : Utiliser exclusivement `.\.venv\Scripts\python.exe`
- **Isolation** : Toutes les dépendances dans `.venv/` pour éviter les conflits
- **Activation** : `.\.venv\Scripts\Activate.ps1` avant utilisation

## 🎯 Guide d'utilisation v4.1

### 👔 Pour les Superviseurs/Gestionnaires

#### Assignation par secteur (nouveau v4.1)
1. **Connexion gestionnaire** : Utilisez vos identifiants superviseur
2. **Onglet "🗺️ Assignation"** : Accédez au nouveau panneau d'assignation
3. **Sélection secteur et équipe** : Choisissez le secteur à assigner et l'équipe destinataire
4. **Assignation en bloc** : Cliquez "🎯 Assigner tout le secteur"
5. **Vérification** : Le tableau des assignations s'actualise automatiquement

#### Export CSV assignations (nouveau v4.1)
1. **Onglet "📥 Export"** : Accédez aux exports spécialisés v4.1
2. **Export CSV Assignations** : Téléchargez le fichier avec colonnes secteur, rue, équipe, statut
3. **Utilisation** : Parfait pour suivi externe ou import dans d'autres outils

### 🎅 Pour les Bénévoles

#### Interface "Mes rues" (nouveau v4.1)
1. **Connexion bénévole** : Connectez-vous avec votre nom d'équipe
2. **Onglet "🏘️ Mes rues"** : Vue filtrée de vos rues assignées uniquement
3. **Mise à jour statuts** : Cliquez "🚀 En cours" ou "✅ Terminée" pour chaque rue
4. **Ajout de notes** : Remplissez numéro civique + commentaire et cliquez "💾 Enregistrer note"
5. **Suivi progression** : Consultez vos métriques en temps réel

#### Gestion des notes par adresse (nouveau v4.1)
1. **Sélection rue** : Développez l'accordéon de la rue souhaitée
2. **Notes existantes** : Consultez les notes déjà saisies
3. **Nouvelle note** : Entrez le numéro civique (ex: 123A) et votre commentaire
4. **Types de notes** : Absent, refus, don reçu, situation particulière...
5. **Validation** : La note est automatiquement horodatée et associée à votre équipe

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
- 📄 **Rapports PDF** avec mise en page professionnelle
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

### 🖼️ Sidebar avec logo intégré
- **Logo professionnel** : Espace dédié 200px en haut de sidebar
- **Positionnement optimal** : Collé au bord supérieur sans espace vide
- **Fallback élégant** : Placeholder festif avec dégradé Guignolée si logo absent
- **Navigation moderne** : Boutons stylisés Accueil/Bénévole/Gestionnaire
- **Branding complet** : Cohérence visuelle avec header festif

### 🎨 Effets de connexion festifs
- **Connexion bénévole** : Effet neige (`st.snow()`) pour ambiance hivernale
- **Connexion gestionnaire** : Effet neige unifié pour cohérence thématique
- **Messages personnalisés** : Accueil par équipe avec design festif

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

## 🔧 Dépannage

### Problèmes de légende
- **Légende invisible** : Appuyez sur F5 pour recharger complètement la page
- **Légende qui clignote** : Normal lors du changement de fond de carte
- **Position incorrecte** : La légende se repositionne automatiquement

### Problèmes de compatibilité Streamlit
- **Erreur use_container_width** : Version récente de Streamlit - l'application s'adapte automatiquement
- **Affichage dégradé** : Mise à jour recommandée vers Streamlit 1.28+
- **Contrôles manquants** : Vérifiez la version folium et streamlit-folium

### Problèmes de compatibilité pandas
- **Erreur "Cannot access attribute 'applymap'"** : Pandas 2.4+ retire applymap - l'application utilise un helper de compatibilité
- **Tables sans style** : Vérifiez la version pandas, le helper `style_map_compat()` gère automatiquement les versions
- **Couleurs manquantes** : Problème temporaire lors du changement de version pandas - redémarrez l'application

### Performance
- **Carte lente** : Réduisez le zoom ou changez de fond de carte
- **Mémoire élevée** : Rechargez l'application avec F5
- **Erreurs OSM** : Vérifiez la connexion internet

### Données
- **Rues manquantes** : Utilisez "Recharger depuis OSM" dans l'onglet Admin
- **Backup corrupt** : Les backups sont vérifiés à la création
- **Données perdues** : Consultez le dossier backups/ pour récupération

## 📝 Support

Développé pour **Le Relais de Mascouche** - Collecte de denrées 2025

---
*Version 3.4 - Interface sidebar complète avec logo intégré et effets festifs*
