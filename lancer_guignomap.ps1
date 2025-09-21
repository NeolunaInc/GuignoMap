# Script de lancement Guigno-Map
# Assure l'activation du venv et l'installation des dépendances

Write-Host " Guigno-Map - Script de lancement" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Yellow

# Vérifier si le venv existe
if (!(Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host " Virtual environment non trouvé. Création..." -ForegroundColor Red
    py -m venv .venv
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

# Activer le venv
Write-Host " Activation du virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Mettre à jour pip
Write-Host " Mise à jour de pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Installer les dépendances si requirements.txt existe
if (Test-Path ".\requirements.txt") {
    Write-Host " Installation des dépendances..." -ForegroundColor Cyan
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { 
        Write-Host " Erreur lors de l'installation des dépendances" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host " requirements.txt non trouvé, installation basique..." -ForegroundColor Yellow
    pip install streamlit pandas folium streamlit-folium
}

# Vérifier que l'app existe
if (!(Test-Path ".\guignomap\app.py")) {
    Write-Host " guignomap/app.py non trouvé" -ForegroundColor Red
    exit 1
}

Write-Host " Prêt à lancer Guigno-Map !" -ForegroundColor Green
Write-Host " Lancement sur http://localhost:8502" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Yellow

# Lancer l'application
python -m streamlit run guignomap/app.py --server.port 8502 --server.headless true
