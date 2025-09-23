# Active l'environnement virtuel en utilisant le chemin correct
<#
.SYNOPSIS
Lance GuignoMap avec options d'initialisation, backup, port et tests.

.PARAMETER InitDb
Initialise la base SQLite si spécifié.

.PARAMETER SkipTests
Saute les tests rapides si spécifié.

.PARAMETER Port
Port Streamlit (défaut: 8501).

.PARAMETER Backup
Effectue un backup DB+Excel si spécifié.

.EXAMPLE
.\lancer_guignomap.ps1 -InitDb -Backup -Port 8502
#>

param(
	[switch]$InitDb = $false,
	[switch]$SkipTests = $false,
	[int]$Port = 8501,
	[switch]$Backup = $false
)

function Write-Info($msg) { Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg)  { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg){ Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host $msg -ForegroundColor Red }

# 1. Créer/activer .venv et installer requirements
if (!(Test-Path ".\.venv\Scripts\python.exe")) {
	Write-Info "Création de l'environnement virtuel .venv..."
	py -m venv .venv
}
Write-Info "Activation de l'environnement virtuel..."
& ".\.venv\Scripts\Activate.ps1"
Write-Info "Installation des dépendances (requirements.txt)..."
try {
	.\.venv\Scripts\pip.exe install --upgrade pip
	.\.venv\Scripts\pip.exe install -U -r requirements.txt --upgrade-strategy eager
	Write-Ok "Dépendances installées."
} catch { Write-Warn "Installation pip échouée (vérifiez requirements.txt)." }

# Vérifications post-install
try {
	.\.venv\Scripts\pip.exe check
	Write-Ok "Pip check passé."
} catch { Write-Warn "Pip check échoué (conflits potentiels)." }
try {
	.\.venv\Scripts\python.exe -c "import plotly,sys; print('Plotly version:', plotly.__version__)"
} catch { Write-Warn "Impossible de vérifier la version Plotly." }

# 2. Set-Location racine et PYTHONPATH
Set-Location "$PSScriptRoot"
$env:PYTHONPATH = (Get-Location).Path
Write-Info "PYTHONPATH exporté: $env:PYTHONPATH"

# 3. Initialisation DB si demandé
if ($InitDb) {
	Write-Info "Initialisation de la base de données..."
	try {
		.\.venv\Scripts\python.exe -c "from guignomap import db; import sqlite3; c=sqlite3.connect('guignomap/guigno_map.db'); db.init_db(c); print('INIT OK')"
		Write-Ok "Base de données initialisée."
	} catch { Write-Warn "Initialisation DB échouée (fichier ou module manquant)." }
}

# 4. Backup si demandé
if ($Backup) {
	$backupDir = "$env:USERPROFILE\Documents\GuignoMap_Backups"
	if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }
	$dbSrc = "guignomap\guigno_map.db"
	$excelSrc = "import\nocivique_cp_complement.xlsx"
	$ts = Get-Date -Format "yyyyMMdd_HHmmss"
	$dbDest = "$backupDir\guigno_map_$ts.db"
	$excelDest = "$backupDir\nocivique_cp_complement_$ts.xlsx"
	$zipPath = "$backupDir\GuignoMap_Backup_$ts.zip"
	$manifest = "$backupDir\manifest_$ts.sha256.txt"
	Write-Info "Backup en cours..."
	$files = @()
	if (Test-Path $dbSrc) {
		Copy-Item $dbSrc $dbDest -Force
		$files += $dbDest
		Write-Ok "DB copiée: $dbDest"
	} else { Write-Warn "DB absente: $dbSrc" }
	if (Test-Path $excelSrc) {
		Copy-Item $excelSrc $excelDest -Force
		$files += $excelDest
		Write-Ok "Excel copié: $excelDest"
	} else { Write-Warn "Excel absent: $excelSrc" }
	if ($files.Count -gt 0) {
		Compress-Archive -Path $files -DestinationPath $zipPath -Force
		Write-Ok "Backup ZIP créé: $zipPath"
		# SHA256 manifest
		$manifestLines = @()
		foreach ($f in $files) {
			try {
				$sha = Get-FileHash $f -Algorithm SHA256
				$manifestLines += "$($sha.Hash) $($sha.Path)"
			} catch { $manifestLines += "SHA256 ERROR $f" }
		}
		$manifestLines | Set-Content $manifest
		Write-Ok "Manifest SHA256: $manifest"
	} else { Write-Warn "Aucun fichier à archiver." }
}

# 5. Tests rapides si non skip
if (-not $SkipTests) {
	Write-Info "Lancement des tests rapides..."
	try {
		.\.venv\Scripts\python.exe -m tests.smoke_db_status_api
		Write-Ok "Test status API OK."
	} catch { Write-Warn "Test status API échoué." }
	try {
		.\.venv\Scripts\python.exe -m tests.smoke_db_missing_api
		Write-Ok "Test missing API OK."
	} catch { Write-Warn "Test missing API échoué." }
} else {
	Write-Info "Tests rapides sautés (--SkipTests)."
}

# 6. Lancement Streamlit
Write-Info "Démarrage de l'application Streamlit sur le port $Port..."
try {
	streamlit run guignomap/app.py --server.port $Port
} catch { Write-Warn "Erreur de lancement Streamlit (vérifiez installation et port)." }