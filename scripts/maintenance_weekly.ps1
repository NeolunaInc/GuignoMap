# ============================================================================
# MAINTENANCE HEBDOMADAIRE GUIGNOMAP
# ============================================================================
# Script PowerShell pour maintenance automatisée hebdomadaire
# Usage: .\scripts\maintenance_weekly.ps1

param(
    [string]$City = "mascouche",
    [string]$ExcelFile = "imports/mascouche_adresses.xlsx"
)

# Configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Couleurs pour output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) { Write-Output $args }
    else { $input | Write-Output }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }
function Write-Info { Write-ColorOutput Cyan $args }

# Vérifier l'environnement
Write-Info "🔍 Vérification de l'environnement..."

if (!(Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "❌ Environnement virtuel non trouvé. Exécutez d'abord le setup."
    exit 1
}

if (!(Test-Path $ExcelFile)) {
    Write-Warning "⚠️  Fichier Excel non trouvé: $ExcelFile"
    Write-Info "Maintenance continuera sans vérification Excel..."
}

# Créer répertoire exports/maintenance si nécessaire
$MaintenanceDir = "exports/maintenance"
if (!(Test-Path $MaintenanceDir)) {
    New-Item -ItemType Directory -Path $MaintenanceDir -Force | Out-Null
    Write-Success "📁 Créé répertoire: $MaintenanceDir"
}

# Date pour nommage des fichiers
$DateStamp = Get-Date -Format "yyyyMMdd_HHmm"

Write-Success "🚀 Début maintenance hebdomadaire - $DateStamp"
Write-Info "   Ville: $City"
Write-Info "   Excel: $ExcelFile"

# 1. VERIFICATION DES ADRESSES
if (Test-Path $ExcelFile) {
    Write-Info "📋 1. Vérification des adresses Excel vs DB..."
    try {
        & ".\.venv\Scripts\python.exe" "scripts\verify_addresses.py" --city $City --file $ExcelFile
        Write-Success "✅ Vérification des adresses terminée"
    }
    catch {
        Write-Warning "⚠️  Erreur lors de la vérification: $_"
    }
}
else {
    Write-Warning "⏭️  Vérification Excel ignorée (fichier manquant)"
}

# 2. ENRICHISSEMENT OSM
Write-Info "🗺️  2. Enrichissement des adresses depuis OSM..."
try {
    & ".\.venv\Scripts\python.exe" "scripts\enrich_addresses_from_osm.py"
    Write-Success "✅ Enrichissement OSM terminé"
}
catch {
    Write-Warning "⚠️  Erreur lors de l'enrichissement OSM: $_"
}

# 3. EXPORT DES STATISTIQUES
Write-Info "📊 3. Export des statistiques..."
$StatsFile = "$MaintenanceDir\stats_$DateStamp.csv"

try {
    # Générer les stats via Python et sauvegarder en CSV
    $StatsScript = @"
import sys
import csv
from pathlib import Path
from datetime import datetime

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from guignomap.database import stats_addresses, extended_stats, stats_by_team

# Récupérer toutes les stats
addr_stats = stats_addresses()
ext_stats = extended_stats()
team_stats = stats_by_team()

# Créer le fichier CSV
with open('$StatsFile', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    
    # En-têtes
    writer.writerow(['Type', 'Métrique', 'Valeur', 'Timestamp'])
    
    # Stats adresses
    timestamp = datetime.now().isoformat()
    writer.writerow(['Adresses', 'Total', addr_stats['total'], timestamp])
    writer.writerow(['Adresses', 'Non assignées', addr_stats['unassigned'], timestamp])
    writer.writerow(['Adresses', 'Assignées', addr_stats['assigned'], timestamp])
    
    # Stats étendues
    writer.writerow(['Rues', 'Total', ext_stats['streets_count'], timestamp])
    writer.writerow(['Rues', 'À faire', ext_stats['todo_streets'], timestamp])
    writer.writerow(['Rues', 'En cours', ext_stats['partial_streets'], timestamp])
    writer.writerow(['Rues', 'Terminées', ext_stats['done_streets'], timestamp])
    
    # Stats équipes
    writer.writerow(['Équipes', 'Total actives', len([t for t in team_stats if t['active']]), timestamp])
    writer.writerow(['Équipes', 'Total', len(team_stats), timestamp])

print(f'Stats exportées vers: $StatsFile')
"@

    $StatsScript | & ".\.venv\Scripts\python.exe" -
    Write-Success "✅ Statistiques exportées: $StatsFile"
}
catch {
    Write-Warning "⚠️  Erreur lors de l'export des stats: $_"
}

# 4. BACKUP DE LA BASE DE DONNÉES
Write-Info "💾 4. Backup de la base de données..."
$BackupFile = "$MaintenanceDir\guigno_map_backup_$DateStamp.db"

try {
    Copy-Item "guignomap\guigno_map.db" $BackupFile
    
    # Compression du backup
    $BackupZip = "$MaintenanceDir\guigno_map_backup_$DateStamp.zip"
    Compress-Archive -Path $BackupFile -DestinationPath $BackupZip -Force
    Remove-Item $BackupFile  # Supprimer la version non compressée
    
    $BackupSize = [math]::Round((Get-Item $BackupZip).Length / 1MB, 2)
    Write-Success "✅ Backup créé: $BackupZip ($BackupSize MB)"
}
catch {
    Write-Warning "⚠️  Erreur lors du backup: $_"
}

# 5. NETTOYAGE DES ANCIENS FICHIERS (garde les 30 derniers jours)
Write-Info "🧹 5. Nettoyage des anciens fichiers de maintenance..."
try {
    $CutoffDate = (Get-Date).AddDays(-30)
    $OldFiles = Get-ChildItem $MaintenanceDir -File | Where-Object { $_.LastWriteTime -lt $CutoffDate }
    
    if ($OldFiles) {
        $OldFiles | Remove-Item -Force
        Write-Success "✅ Supprimés $($OldFiles.Count) anciens fichiers"
    }
    else {
        Write-Info "ℹ️  Aucun ancien fichier à supprimer"
    }
}
catch {
    Write-Warning "⚠️  Erreur lors du nettoyage: $_"
}

# RÉSUMÉ FINAL
Write-Success ""
Write-Success "🎉 MAINTENANCE HEBDOMADAIRE TERMINÉE"
Write-Success "=" * 50
Write-Info "Fichiers générés:"
if (Test-Path $StatsFile) { Write-Info "  📊 Stats: $StatsFile" }
if (Test-Path $BackupZip) { Write-Info "  💾 Backup: $BackupZip" }
Write-Info ""
Write-Info "Pour programmer cette maintenance:"
Write-Info "  schtasks /create /tn `"GuignoMap Weekly`" /tr `"powershell.exe -File $(Join-Path $PWD 'scripts\maintenance_weekly.ps1')`" /sc weekly /d SUN /st 02:00"
Write-Success ""