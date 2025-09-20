# [GM] BEGIN cleanup_workspace.ps1
param(
  [switch]$Apply = $false,
  [int]$KeepDays = 7
)
$ErrorActionPreference = 'Stop'
Write-Host "=== GuignoMap Cleanup (Apply=$Apply, KeepDays=$KeepDays) ==="

function Remove-IfExists($path) {
  if (Test-Path $path) {
    if ($Apply) { Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Host ("{0} {1}" -f ($(if ($Apply) {'DEL'} else {'DRY'}), $path))
  }
}

# 1) caches/dev
@('.pytest_cache',' .ruff_cache') | ForEach-Object { Remove-IfExists $_.Trim() }

# 2) exports volatils
Get-ChildItem -Path 'exports' -File -ErrorAction SilentlyContinue `
  | Where-Object { $_.Name -match '^(status_counts_|unassigned_|sanity_)' } `
  | ForEach-Object { if ($Apply) { Remove-Item $_.FullName -Force } ; Write-Host ("{0} {1}" -f ($(if ($Apply) {'DEL'} else {'DRY'}), $_.FullName)) }

# 3) rapports ponctuels
Get-ChildItem -Path . -File -Filter 'export*.txt' -ErrorAction SilentlyContinue `
  | ForEach-Object { if ($Apply) { Remove-Item $_.FullName -Force } ; Write-Host ("{0} {1}" -f ($(if ($Apply) {'DEL'} else {'DRY'}), $_.FullName)) }
Get-ChildItem -Path . -File -Filter 'GuignoMap_code_export_*.txt' -ErrorAction SilentlyContinue `
  | ForEach-Object { if ($Apply) { Remove-Item $_.FullName -Force } ; Write-Host ("{0} {1}" -f ($(if ($Apply) {'DEL'} else {'DRY'}), $_.FullName)) }
Get-ChildItem -Path . -File -Filter 'pylance_errors_report_*.txt' -ErrorAction SilentlyContinue `
  | ForEach-Object { if ($Apply) { Remove-Item $_.FullName -Force } ; Write-Host ("{0} {1}" -f ($(if ($Apply) {'DEL'} else {'DRY'}), $_.FullName)) }

# 4) backups volumineux (ne pas toucher à la DB active)
if (Test-Path 'backups') {
  Get-ChildItem backups -Recurse -File | ForEach-Object {
    $age = (New-TimeSpan -Start $_.LastWriteTime -End (Get-Date)).Days
    if ($age -ge $KeepDays) {
      if ($Apply) { Remove-Item $_.FullName -Force }
      Write-Host ("{0} {1}" -f ($(if ($Apply) {'DEL'} else {'DRY'}), $_.FullName))
    }
  }
}

# 5) legacy (optionnel : notifie seulement en dry-run)
if (Test-Path 'legacy') {
  Write-Host "INFO legacy/ détecté. Supprimer via CLEAN-4 si validé."
}

Write-Host "=== FIN cleanup ==="
# [GM] END cleanup_workspace.ps1