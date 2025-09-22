# Active l'environnement virtuel en utilisant le chemin correct
.\.venv\Scripts\Activate.ps1

# Force l'ajout du dossier courant au chemin de recherche de Python
$env:PYTHONPATH = "."

# Lance l'application Streamlit
Write-Host "Lancement de l'application GuignoMap..." -ForegroundColor Green
streamlit run guignomap/app.py