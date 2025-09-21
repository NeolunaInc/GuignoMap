# PROBLÈME CONNECTIVITÉ SUPABASE IPv6

## 🚨 Situation actuelle
- Supabase PostgreSQL utilise **uniquement IPv6** pour cette instance
- L'host `db.kdxqspmfycnwzzrmhzpa.supabase.co` résout vers: `2600:1f11:4e2:e202:6514:7431:494f:c00f`
- Votre réseau local ne supporte **pas IPv6 global** (seulement liaison locale)

## ❌ Tests échoués
```powershell
ping db.kdxqspmfycnwzzrmhzpa.supabase.co  # DNS fail
Test-NetConnection -ComputerName db.kdxqspmfycnwzzrmhzpa.supabase.co -Port 5432  # DNS fail
ping -6 2600:1f11:4e2:e202:6514:7431:494f:c00f  # IPv6 network unreachable
```

## ✅ Solutions disponibles

### 1. IMMÉDIAT - Développement local (Recommandé)
```toml
# Dans .streamlit/secrets.toml
[database]
# Commentez Supabase et utilisez SQLite local
# url = "postgresql://postgres:4everSab!2304@db.kdxqspmfycnwzzrmhzpa.supabase.co:5432/postgres"
url = "sqlite:///./guignomap/guigno_map.db"
```

### 2. PRODUCTION - Solutions IPv6

#### Option A: Configuration FAI/Réseau
- Contacter votre FAI pour activer IPv6
- Configurer tunnel IPv6 (ex: Hurricane Electric)
- Activer IPv6 sur votre routeur/modem

#### Option B: Nouveau projet Supabase
1. Créer un nouveau projet Supabase
2. Espérer obtenir une instance avec support IPv4
3. Migrer la base de données

#### Option C: Cloudflare Tunnel
```bash
# Installer cloudflared
# Créer un tunnel vers Supabase
cloudflared tunnel --hostname myapp.trycloudflare.com --url db.kdxqspmfycnwzzrmhzpa.supabase.co:5432
```

### 3. STREAMLIT CLOUD - Pas de problème
Une fois déployé sur **Streamlit Cloud**, l'IPv6 sera supporté.

## 🔧 Configuration immédiate

Pour continuer le développement **MAINTENANT**:

```powershell
# 1. Basculer vers SQLite local dans secrets.toml
# 2. Tester la connexion locale
.\.venv\Scripts\python.exe -c "from src.database.connection import test_connection; test_connection()"

# 3. Migrer les données SQLite vers PostgreSQL plus tard
.\.venv\Scripts\python.exe scripts/migrate_sqlite_to_postgres.py
```

## 📈 Plan de déploiement

1. **MAINTENANT**: Développement avec SQLite local
2. **PLUS TARD**: Résoudre IPv6 ou nouveau projet Supabase  
3. **DÉPLOIEMENT**: Streamlit Cloud (IPv6 natif)
4. **MIGRATION**: Données SQLite → PostgreSQL

## 🌐 Vérification IPv6 système
```powershell
ipconfig /all | findstr "IPv6"
# Résultat: Seulement liaison locale (fe80::...)
# Besoin: Adresse IPv6 globale (2xxx::/16)
```