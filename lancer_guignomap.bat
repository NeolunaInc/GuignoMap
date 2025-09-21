@echo off
echo ========================================
echo       GuignoMap - Relais de Mascouche
echo ========================================
echo.
echo Activation de l'environnement virtuel...
echo.

REM Change vers le répertoire de l'application
cd /d "%~dp0"

REM Active l'environnement virtuel
call .venv\Scripts\activate

echo Lancement de l'application...
echo.

REM Lance Streamlit avec l'application
python -m streamlit run guignomap/app.py --server.port 8501 --server.headless true

pause