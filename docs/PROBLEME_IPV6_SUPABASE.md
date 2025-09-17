# PROBL√àME CONNECTIVIT√â SUPABASE IPv6

## üö® Situation actuelle
- Supabase PostgreSQL utilise **uniquement IPv6** pour cette instance
- L'host `db.kdxqspmfycnwzzrmhzpa.supabase.co` r√©sout vers: `2600:1f11:4e2:e202:6514:7431:494f:c00f`
- Votre r√©seau local ne supporte **pas IPv6 global** (seulement liaison locale)

## ‚ùå Tests √©chou√©s
```powershell
ping db.kdxqspmfycnwzzrmhzpa.supabase.co  # DNS fail
Test-NetConnection -ComputerName db.kdxqspmfycnwzzrmhzpa.supabase.co -Port 5432  # DNS fail
ping -6 2600:1f11:4e2:e202:6514:7431:494f:c00f  # IPv6 network unreachable
```

## ‚úÖ Solutions disponibles

### 1. IMM√âDIAT - D√©veloppement local (Recommand√©)
```toml
# Dans .streamlit/secrets.toml
[database]
# Commentez Supabase et utilisez SQLite local
# url = "postgresql://postgres:4everSab!2304@db.kdxqspmfycnwzzrmhzpa.supabase.co:5432/postgres"
url = "sqlite:///./guignomap/guigno_map.db"
```

### 2. PRODUCTION - Solutions IPv6

#### Option A: Configuration FAI/R√©seau
- Contacter votre FAI pour activer IPv6
- Configurer tunnel IPv6 (ex: Hurricane Electric)
- Activer IPv6 sur votre routeur/modem

#### Option B: Nouveau projet Supabase
1. Cr√©er un nouveau projet Supabase
2. Esp√©rer obtenir une instance avec support IPv4
3. Migrer la base de donn√©es

#### Option C: Cloudflare Tunnel
```bash
# Installer cloudflared
# Cr√©er un tunnel vers Supabase
cloudflared tunnel --hostname myapp.trycloudflare.com --url db.kdxqspmfycnwzzrmhzpa.supabase.co:5432
```

### 3. STREAMLIT CLOUD - Pas de probl√®me
Une fois d√©ploy√© sur **Streamlit Cloud**, l'IPv6 sera support√©.

## üîß Configuration imm√©diate

Pour continuer le d√©veloppement **MAINTENANT**:

```powershell
# 1. Basculer vers SQLite local dans secrets.toml
# 2. Tester la connexion locale
.\.venv\Scripts\python.exe -c "from src.database.connection import test_connection; test_connection()"

# 3. Migrer les donn√©es SQLite vers PostgreSQL plus tard
.\.venv\Scripts\python.exe scripts/migrate_sqlite_to_postgres.py
```

## üìà Plan de d√©ploiement

1. **MAINTENANT**: D√©veloppement avec SQLite local
2. **PLUS TARD**: R√©soudre IPv6 ou nouveau projet Supabase  
3. **D√âPLOIEMENT**: Streamlit Cloud (IPv6 natif)
4. **MIGRATION**: Donn√©es SQLite ‚Üí PostgreSQL

## üåê V√©rification IPv6 syst√®me
```powershell
ipconfig /all | findstr "IPv6"
# R√©sultat: Seulement liaison locale (fe80::...)
# Besoin: Adresse IPv6 globale (2xxx::/16)
```