# Guide de Gouvernance des Données - GuignoMap

## Vue d'ensemble

Ce document décrit la stratégie de gouvernance des données pour GuignoMap v4.2, couvrant la gestion des sources autoritatives, les processus d'import, la déduplication, et l'enrichissement automatique.

## 🏛️ Sources de Données Autoritatives

### Source Primaire : Excel Municipal

**Fichier autoritatif** : `imports/mascouche_adresses.xlsx`

**Caractéristiques** :
- ✅ **Source officielle** de la municipalité
- ✅ **Données structurées** : adresse, secteur, coordonnées GPS
- ✅ **Mise à jour périodique** par les services municipaux
- ✅ **Format standardisé** pour import automatisé

**Colonnes attendues** :
```
Adresse civique | Rue | Secteur | Latitude | Longitude
```

**Responsabilités** :
- **Municipalité** : Maintient la précision et l'exhaustivité
- **Équipe technique** : Import et validation des données
- **Gestionnaires** : Assignation des équipes et suivi

### Source Secondaire : OpenStreetMap (OSM)

**Usage** : Enrichissement automatique des coordonnées manquantes

**Avantages** :
- 🗺️ **Couverture géographique** étendue
- 🔄 **Données ouvertes** et collaboratives
- ⚡ **API géocodage** gratuite et performante

**Limitations** :
- ⚠️ **Précision variable** selon la zone
- ⚠️ **Pas toujours à jour** pour nouveaux développements
- ⚠️ **Format d'adresse** peut différer des standards municipaux

## 🔄 Processus d'Import "Swap" Intelligent

### Philosophie

L'import utilise une stratégie **"swap intelligent"** qui :
1. **Préserve** toutes les assignations d'équipes existantes
2. **Met à jour** les données d'adresses (coordonnées, secteurs)
3. **Ajoute** les nouvelles adresses sans perte
4. **Identifie** les adresses supprimées pour révision manuelle

### Étapes du Processus

#### 1. Préparation et Validation

```bash
# Vérification du fichier Excel
python scripts/verify_addresses.py --city mascouche --file imports/mascouche_adresses.xlsx
```

**Validations** :
- ✅ Format des colonnes conforme
- ✅ Coordonnées GPS dans les limites géographiques
- ✅ Pas de doublons dans le fichier source
- ✅ Encodage UTF-8 correct

#### 2. Import avec Préservation

```bash
# Import intelligent avec préservation des assignations
python scripts/import_city_excel.py --city mascouche --file imports/mascouche_adresses.xlsx
```

**Algorithme** :
1. **Génération des clés** : `addr_key` normalisée pour chaque adresse
2. **Correspondance** : Mapping ancien ↔ nouveau via `addr_key`
3. **Préservation** : Conservation des assignations existantes
4. **Enrichissement** : Ajout des nouvelles données (secteur, coordonnées)
5. **Ajout** : Insertion des nouvelles adresses avec statut "non assignée"

#### 3. Post-Import et Validation

```bash
# Vérification post-import
python scripts/check_addresses.py

# Export pour révision
python tools/quick_sanity.py
```

## 🔑 Gestion des Doublons via `addr_key`

### Génération de la Clé

**Fonction** : `_normalize_text()` dans `guignomap/imports.py`

**Algorithme** :
```python
def _normalize_text(s):
    # 1. Conversion en string et nettoyage
    text = str(s).strip()
    
    # 2. Suppression des accents (NFD + suppression diacritiques)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # 3. Minuscules et compression espaces
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
```

**Exemples de normalisation** :
```
"123 Rue Saint-Étienne"  → "123 rue saint-etienne"
"456  Avenue  du Parc"   → "456 avenue du parc"  
"789 Boul. René-Lévesque" → "789 boul. rene-levesque"
```

### Détection et Résolution

**Stratégie** :
1. **Détection automatique** : Même `addr_key` = doublon potentiel
2. **Résolution intelligente** : Préférence à la donnée la plus récente/complète
3. **Logging détaillé** : Traçabilité de toutes les résolutions
4. **Rapport de conflit** : Export des cas ambigus pour révision manuelle

**Cas d'usage** :
- ✅ **Variations d'écriture** : "St-Étienne" vs "Saint-Étienne"
- ✅ **Espaces multiples** : "123  Rue" vs "123 Rue"
- ✅ **Casse différente** : "AVENUE" vs "avenue"
- ⚠️ **Doublons légitimes** : Même rue, numéros différents (détection par numéro civique)

## 🗺️ Routine d'Enrichissement OSM

### Déclenchement Automatique

**Script** : `scripts/enrich_addresses_from_osm.py`

**Quand** :
- 🔄 **Maintenance hebdomadaire** (automatique)
- 📥 **Post-import** d'un nouveau fichier Excel
- 🆘 **À la demande** pour corriger des coordonnées manquantes

### Processus d'Enrichissement

#### 1. Identification des Cibles

```sql
-- Adresses sans coordonnées précises
SELECT * FROM addresses 
WHERE latitude IS NULL 
   OR longitude IS NULL 
   OR (latitude = 0 AND longitude = 0)
```

#### 2. Géocodage Intelligent

**API utilisée** : Overpass API (OpenStreetMap)

**Stratégie de requête** :
1. **Recherche exacte** : Adresse complète + ville
2. **Recherche approximative** : Rue + numéro si échec
3. **Recherche par rue** : Rue seulement + interpolation
4. **Fallback manuel** : Marquage pour révision humaine

#### 3. Validation et Application

**Validations** :
- ✅ **Limites géographiques** : Coordonnées dans les bounds de la ville
- ✅ **Cohérence** : Distance raisonnable des adresses voisines
- ✅ **Qualité** : Score de confiance OSM > seuil

**Application** :
- 🔄 **Mise à jour automatique** si validation OK
- ⚠️ **Mise en attente** si validation douteuse
- 📝 **Logging détaillé** de tous les enrichissements

### Cache et Performance

**Fichier cache** : `guignomap/osm_cache.json` (non tracké Git)

**Avantages** :
- ⚡ **Performance** : Évite les requêtes répétées
- 🌐 **Limites API** : Respect des quotas OSM
- 🔄 **Persistance** : Cache survit aux redémarrages

**Gestion** :
- 🗑️ **Nettoyage automatique** : Cache expiré après 30 jours
- 🔄 **Invalidation** : Possible via paramètre `--refresh-cache`
- 📊 **Métriques** : Tracking hit/miss ratio

## 📋 Workflows de Maintenance

### Maintenance Hebdomadaire Automatisée

**Script** : `scripts/maintenance_weekly.ps1`

**Actions** :
1. ✅ **Vérification Excel→DB** : Cohérence des données
2. 🗺️ **Enrichissement OSM** : Mise à jour coordonnées
3. 📊 **Export statistiques** : Métriques pour suivi
4. 💾 **Backup base de données** : Sauvegarde compressée
5. 🧹 **Nettoyage** : Suppression anciens fichiers

**Planification recommandée** :
```powershell
# Tous les dimanches à 2h du matin
schtasks /create /tn "GuignoMap Weekly" /tr "powershell.exe -File scripts\maintenance_weekly.ps1" /sc weekly /d SUN /st 02:00
```

### Maintenance Corrective

**Symptômes nécessitant intervention** :
- 🚨 **Écarts Excel→DB** détectés
- 📍 **Coordonnées manquantes** > 5% des adresses
- 👥 **Assignations perdues** après import
- 🐛 **Erreurs répétées** dans les logs

**Actions correctives** :
```bash
# Diagnostic complet
python scripts/check_addresses.py

# Réparation assignations
python scripts/verify_addresses.py --city mascouche --file imports/mascouche_adresses.xlsx

# Ré-enrichissement forcé
python scripts/enrich_addresses_from_osm.py --refresh-cache

# Tests de non-régression
python -m pytest tests/ -v
```

## 🔐 Sécurité et Intégrité

### Contrôles d'Intégrité

1. **Validation des imports** : Schéma strict, types de données
2. **Transactions atomiques** : Rollback automatique en cas d'erreur
3. **Checksums** : Vérification intégrité des fichiers Excel
4. **Audit trail** : Logging de toutes les modifications

### Backup et Récupération

**Stratégie 3-2-1** :
- 📦 **3 copies** : Production + 2 backups
- 💾 **2 médias** : Local + exports cloud (optionnel)
- 🏢 **1 site distant** : Repository GitHub

**Récupération** :
```bash
# Restauration depuis backup
cp exports/maintenance/guigno_map_backup_YYYYMMDD.zip .
unzip guigno_map_backup_YYYYMMDD.zip
cp guigno_map_backup_YYYYMMDD.db guignomap/guigno_map.db

# Validation post-restauration
python tools/quick_sanity.py
```

## 📊 Métriques et Monitoring

### KPIs de Gouvernance

**Qualité des données** :
- 📍 **Géolocalisation** : % adresses avec coordonnées précises
- 🎯 **Assignations** : % adresses assignées aux équipes
- 🔄 **Fraîcheur** : Délai depuis dernière mise à jour Excel
- ✅ **Cohérence** : % conformité Excel ↔ DB

**Performance système** :
- ⚡ **Import** : Temps traitement fichier Excel
- 🗺️ **OSM enrichissement** : Taux succès géocodage
- 💾 **Base de données** : Taille, performance requêtes
- 🧹 **Maintenance** : Statut dernière exécution

### Tableaux de Bord

**Export automatique** : `exports/maintenance/stats_YYYYMMDD.csv`

**Métriques disponibles** :
```csv
Type,Métrique,Valeur,Timestamp
Adresses,Total,18483,2025-09-18T10:30:00
Adresses,Non assignées,14273,2025-09-18T10:30:00
Adresses,Assignées,4210,2025-09-18T10:30:00
Rues,Total,892,2025-09-18T10:30:00
Équipes,Total actives,12,2025-09-18T10:30:00
```

---

## 🚀 Évolution Future

### Améliorations Prévues

1. **API temps réel** : Synchronisation automatique avec systèmes municipaux
2. **Machine Learning** : Détection intelligente des anomalies
3. **Dashboard web** : Visualisation métriques en temps réel
4. **Notifications** : Alertes automatiques sur événements critiques

### Roadmap Gouvernance

- **Q4 2025** : Automatisation complète maintenance
- **Q1 2026** : Intégration API municipale directe
- **Q2 2026** : Dashboard analytique avancé
- **Q3 2026** : Certification qualité données ISO 27001

---

*Document version 1.0 - GuignoMap v4.2*  
*Dernière mise à jour : Septembre 2025*