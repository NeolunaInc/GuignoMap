# GuignoMap - Script de lancement PowerShell
# Relais de Mascouche

Write-Host "========================================" -ForegroundColor Green
Write-Host "       GuignoMap - Relais de Mascouche" -ForegroundColor Green  
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
Write-Host ""

# Change vers le répertoire de l'application
Set-Location $PSScriptRoot

# Active l'environnement virtuel
& .\.venv\Scripts\Activate.ps1

Write-Host "Lancement de l'application..." -ForegroundColor Yellow
Write-Host ""

# Lance Streamlit avec l'application
& python -m streamlit run guignomap/app.py --server.port 8501 --server.headless true

Read-Host "Appuyez sur Entrée pour fermer..."