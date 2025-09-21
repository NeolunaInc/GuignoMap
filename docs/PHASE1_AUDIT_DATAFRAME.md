# 🔍 AUDIT DATAFRAME - RAPPORT COMPLET

## 📊 SYNTHÈSE EXECUTIVE

**Statut** : Migration critique nécessaire  
**Impact** : 🔴 BLOQUANT - L'application ne peut pas fonctionner sans corrections  
**Scope** : Principalement `app.py` (38 occurrences) + `db_v5.py` (corrections mineures)

## 📋 TABLEAU DE MAPPING DÉTAILLÉ

| Fichier | Ligne | Fonction/Contexte | Pattern Détecté | Type Attendu | Type Fourni | Criticité | Usage |
|---------|-------|------------------|-----------------|--------------|-------------|-----------|-------|
| **app.py** | 371 | render_admin_dashboard() | `pd.DataFrame(teams_stats)` | DataFrame | List[Dict] | 🟢 OK | Conversion explicite |
| **app.py** | 401 | render_admin_dashboard() | `st.dataframe(teams_stats)` | DataFrame | List[Dict] | 🟡 MINOR | Affichage direct |
| **app.py** | 506-509 | create_map() | `df.columns`, `row['name']` | DataFrame | **PROBLÈME** | 🔴 CRITIQUE | Lookup géospatial |
| **app.py** | 1034 | render_team_dashboard() | `df_team[df_team['name'] == street_name]` | DataFrame | DataFrame | 🟢 OK | Filtrage |
| **app.py** | 1122 | render_team_dashboard() | `st.dataframe(notes)` | DataFrame | List[Dict] | 🟡 MINOR | Affichage |
| **app.py** | 1215 | render_supervisor_dashboard() | `st.dataframe(recent)` | DataFrame | List[Dict] | 🟡 MINOR | Affichage |
| **app.py** | 1292 | render_quick_admin() | `st.dataframe(teams_df)` | DataFrame | List[Dict] | 🟡 MINOR | Affichage |
| **app.py** | 1421 | render_admin() | `st.dataframe(recent)` | DataFrame | List[Dict] | 🟡 MINOR | Affichage |
| **app.py** | 1442 | render_admin() | `st.dataframe(teams_df)` | DataFrame | List[Dict] | 🟡 MINOR | Affichage |
| **app.py** | 1466 | bulk_assignation() | `st.dataframe(df_disp)` | DataFrame | DataFrame | 🟢 OK | Affichage filtré |
| **app.py** | 1640 | bulk_assignation() | `st.dataframe(df_disp)` | DataFrame | DataFrame | 🟢 OK | Affichage final |
| **app.py** | 1717 | export_panel() | `pd.DataFrame(assignations_data).to_csv()` | DataFrame | List[Dict] | 🟢 OK | Export CSV |

## 🎯 POINTS DE CONVERSION CRITIQUES

### 🔴 CRITIQUE - Ligne 506-509 (create_map)
```python
# PROBLÈME ACTUEL:
if df:  # df est List[Dict] mais code attend DataFrame
    for idx, row in enumerate(df):
        name = str(row['name']) if 'name' in df.columns else ''  # ❌ .columns sur une liste
```

**Solution** : Conversion DataFrame dans `db_v5.list_streets()` OU conversion à l'interface UI.

### 🟡 MINEUR - Fonctions st.dataframe()
```python
# PROBLÈME RÉCURRENT:
st.dataframe(teams_stats)  # teams_stats = List[Dict], streamlit accepte mais préfère DataFrame
```

**Solution** : Conversion `pd.DataFrame()` avant affichage.

## 📋 PLAN DE PATCH ATOMIQUE

### Étape 1: CRITIQUE - Corriger create_map() 
**Fichier** : `app.py` lignes 506-509  
**Action** : Convertir l'itération liste vers DataFrame
```python
# AVANT:
if df:  # Liste
    for idx, row in enumerate(df):
        name = str(row['name']) if 'name' in df.columns else ''

# APRÈS:
if not df.empty:  # DataFrame
    for idx, row in df.iterrows():
        name = str(row['name']) if 'name' in df.columns else ''
```

### Étape 2: MINEUR - Conversions st.dataframe()
**Fichiers** : `app.py` lignes 401, 1122, 1215, 1292, 1421, 1442  
**Action** : Wrapper avec `pd.DataFrame()` si nécessaire
```python
# Pattern:
if data:  # Si liste non vide
    st.dataframe(pd.DataFrame(data))
else:
    st.info("Aucune donnée")
```

### Étape 3: VALIDATION - db_v5.py types retour
**Fichier** : `db_v5.py`  
**Action** : Valider que `list_streets()` retourne bien un DataFrame
```python
# Dans list_streets():
return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['id', 'name', 'sector', 'team', 'status'])
```

## 🔧 SCRIPTS POWERSHELL VALIDATION

### Script 1: Audit DataFrame patterns
```powershell
# Chercher tous les patterns DataFrame problématiques
Select-String -Path .\guignomap\app.py -Pattern '\.columns|\.iterrows|\.empty|\.loc\[|\.iloc\[' -CaseSensitive | 
  Select-Object LineNumber, Line | Format-Table -Auto
```

### Script 2: Variables qui reçoivent des données DB
```powershell
# Chercher les assignations de fonctions db.*
Select-String -Path .\guignomap\app.py -Pattern '\s*\w+\s*=\s*db\.\w+\(' -CaseSensitive |
  Select-Object LineNumber, Line
```

### Script 3: Utilisation st.dataframe()
```powershell
# Chercher tous les st.dataframe pour vérifier les types
Select-String -Path .\guignomap\app.py -Pattern 'st\.dataframe\(' -CaseSensitive |
  Select-Object LineNumber, Line
```

## 📊 DÉTAILS TECHNIQUES PAR FONCTION

### create_map(df, geo) - LIGNE 506
**Problème** : `df` passé comme paramètre, supposé DataFrame mais reçoit List[Dict]
**Source** : Appelé depuis dashboard avec `df = db.list_streets(team=team_id)`
**Solution** : `db.list_streets()` doit retourner DataFrame

### render_*_dashboard() - Multiples lignes
**Problème** : `st.dataframe()` reçoit List[Dict] au lieu de DataFrame
**Impact** : Fonctionne mais sous-optimal, pas de tri/filtrage UI
**Solution** : Conversion `pd.DataFrame()` avant affichage

## 🚨 ACTIONS REQUISES IMMÉDIATEMENT

1. **Corriger create_map()** - BLOQUANT pour carte géospatiale
2. **Valider db_v5.list_streets()** - Assurer retour DataFrame
3. **Wrapper st.dataframe()** - Optimiser affichage

## 📝 QUESTIONS POUR VALIDATION

1. **Colonnes exactes** de `list_streets()` : Confirmer schema ['id', 'name', 'sector', 'team', 'status', 'notes'?]
2. **Performance** : Préférer conversion côté données (db_v5) ou côté UI (app.py) ?
3. **Compatibilité** : Maintenir retro-compatibilité avec ancien `db.py` ?

## ✅ VALIDATION POST-PATCH

```powershell
# Tester l'application après patch
.\.venv\Scripts\python.exe -c "
import sys; sys.path.append('guignomap'); 
import db_v5; 
df = db_v5.list_streets(); 
print(f'Type: {type(df)}, Shape: {df.shape if hasattr(df, \"shape\") else \"N/A\"}')
"

# Tester création carte
.\.venv\Scripts\python.exe -c "
import sys; sys.path.append('guignomap'); 
import app; import db_v5; 
df = db_v5.list_streets(); 
print(f'create_map compatible: {hasattr(df, \"columns\")}')
"
```