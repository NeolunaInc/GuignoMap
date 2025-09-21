# =============================================================================
# SCRIPTS POWERSHELL - VALIDATION DATAFRAME
# =============================================================================

Write-Host "🔍 AUDIT DATAFRAME - SCRIPTS DE VALIDATION" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

Write-Host "`n1️⃣ PATTERNS DATAFRAME PROBLÉMATIQUES" -ForegroundColor Yellow
Write-Host "Recherche: .columns, .iterrows, .empty, .loc[], .iloc[]" -ForegroundColor Gray
Select-String -Path .\guignomap\app.py -Pattern '\.columns|\.iterrows|\.empty|\.loc\[|\.iloc\[' -CaseSensitive | 
  Select-Object LineNumber, Line | Format-Table -Auto

Write-Host "`n2️⃣ ASSIGNATIONS DE FONCTIONS DB" -ForegroundColor Yellow  
Write-Host "Recherche: variables = db.fonction()" -ForegroundColor Gray
Select-String -Path .\guignomap\app.py -Pattern '\s*\w+\s*=\s*db\.\w+\(' -CaseSensitive |
  Select-Object LineNumber, Line | Format-Table -Auto

Write-Host "`n3️⃣ UTILISATION ST.DATAFRAME" -ForegroundColor Yellow
Write-Host "Recherche: st.dataframe() pour vérifier les types" -ForegroundColor Gray  
Select-String -Path .\guignomap\app.py -Pattern 'st\.dataframe\(' -CaseSensitive |
  Select-Object LineNumber, Line | Format-Table -Auto

Write-Host "`n4️⃣ FONCTIONS DB QUI RETOURNENT DES DONNÉES" -ForegroundColor Yellow
Write-Host "Recherche: Fonctions db_v5 qui peuvent retourner listes vs DataFrames" -ForegroundColor Gray
Select-String -Path .\guignomap\db_v5.py -Pattern 'def (list_|get_|stats_|teams|recent_)' -CaseSensitive |
  Select-Object LineNumber, Line | Format-Table -Auto

Write-Host "`n5️⃣ IMPORTS PANDAS DANS APP.PY" -ForegroundColor Yellow  
Write-Host "Recherche: import pandas et pd.DataFrame" -ForegroundColor Gray
Select-String -Path .\guignomap\app.py -Pattern 'import pandas|pd\.DataFrame' -CaseSensitive |
  Select-Object LineNumber, Line | Format-Table -Auto

Write-Host "`n✅ RAPPORT COMPLET GÉNÉRÉ DANS: AUDIT_DATAFRAME.md" -ForegroundColor Green