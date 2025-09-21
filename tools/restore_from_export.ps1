param(
  [string]$ExportPath = ".\export_backup.txt"
)
if(!(Test-Path $ExportPath)){ throw "Fichier introuvable: $ExportPath" }

Add-Type -AssemblyName 'System.IO'
Add-Type -AssemblyName 'System.Text'
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-FileUtf8LF([string]$RelPath,[string]$Content){
  $OutPath = Join-Path -Path (Get-Location) -ChildPath $RelPath
  $Dir = Split-Path $OutPath
  New-Item -ItemType Directory -Force -Path $Dir | Out-Null
  # Normalise les fins de ligne -> LF
  $lf = $Content -replace "`r`n","`n" -replace "`r","`n"
  $fs = [System.IO.File]::Open($OutPath,[System.IO.FileMode]::Create,[System.IO.FileAccess]::Write,[System.IO.FileShare]::Read)
  $sw = New-Object System.IO.StreamWriter($fs,$Utf8NoBom)
  $sw.Write($lf); $sw.Flush(); $sw.Close()
  Write-Host " Écrit: $RelPath"
}

$lines   = Get-Content -LiteralPath $ExportPath -Encoding UTF8
$current = $null
$inCode  = $false
$buffer  = New-Object System.Collections.Generic.List[string]
$written = New-Object System.Collections.Generic.List[string]

foreach($line in $lines){
  if(-not $inCode){
    # Détecte un header de fichier
    if($line -match '^\s*##\s*FICHIER\s+\d+\s*:\s*(.+)$'){
      $current = $Matches[1].Trim()
    }
    # Début d'un bloc ```... (peut être ```python, ```css, etc.)
    elseif($line -match '^\s*```'){
      $inCode = $true; $buffer.Clear()
    }
  } else {
    # Fin de bloc ```
    if($line -match '^\s*```'){
      $inCode = $false
      if($current){
        Write-FileUtf8LF -RelPath $current -Content ($buffer -join "`n")
        $written.Add($current) | Out-Null
        $current = $null
      }
    } else {
      $buffer.Add($line) | Out-Null
    }
  }
}

if($written.Count -eq 0){ throw "Aucun bloc écrit. Vérifie la structure des ``` dans l'export." }
"TOTAL fichiers écrits: $($written.Count)"
$written | Sort-Object | ForEach-Object { " - $_" }
