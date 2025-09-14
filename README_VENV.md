# 🐍 GuignoMap - Instructions d'environnement virtuel

## 🎯 Avantages de l'environnement virtuel

✅ **Isolation des dépendances** : Évite les conflits entre projets  
✅ **Versions spécifiques** : Garantit la reproductibilité  
✅ **Facilité de déploiement** : Package complet et maîtrisé  

## 🚀 Utilisation

### Option 1 - Scripts automatiques (Recommandé)
```cmd
# Double-cliquez sur un de ces fichiers :
lancer_guignomap.bat          # Script Batch
lancer_guignomap.ps1          # Script PowerShell
```

### Option 2 - Activation manuelle
```cmd
# 1. Activer l'environnement virtuel
.venv\Scripts\activate

# 2. Lancer l'application
python -m streamlit run guignomap/app.py

# 3. Désactiver (optionnel)
deactivate
```

### Option 3 - PowerShell
```powershell
# 1. Activer l'environnement virtuel
.\.venv\Scripts\Activate.ps1

# 2. Lancer l'application
python -m streamlit run guignomap/app.py
```

## 🔧 Gestion des dépendances

### Installer de nouveaux packages
```cmd
# Avec l'environnement activé :
pip install nom_du_package

# Mettre à jour requirements.txt :
pip freeze > requirements.txt
```

### Recréer l'environnement
```cmd
# Supprimer l'ancien environnement
rmdir /s .venv

# Recréer
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 📊 Status actuel
- ✅ Environnement virtuel créé : `.venv/`
- ✅ Dépendances installées et testées
- ✅ Scripts de lancement mis à jour
- ✅ `.gitignore` configuré