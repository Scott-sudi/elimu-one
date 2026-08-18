# Surveille Téléchargements / Bureau pour google-services.json
# et le copie dans android/app/ puis signale le succès.

$ErrorActionPreference = "Continue"
$destDir = "C:\Users\Elisée\Desktop\IK\kalunga-school\mobile\kalunga_parents\android\app"
$dest = Join-Path $destDir "google-services.json"
$watchDirs = @(
  "$env:USERPROFILE\Downloads",
  "$env:USERPROFILE\Téléchargements",
  "$env:USERPROFILE\Desktop",
  "$env:USERPROFILE\Bureau",
  "C:\Users\Elisée\Desktop",
  "C:\Users\Elisée\Downloads"
) | Select-Object -Unique

Write-Host "Watching for google-services.json ..."
Write-Host "Destination: $dest"
Write-Host "Folders:"
$watchDirs | ForEach-Object { Write-Host " - $_" }

function Try-Install([string]$src) {
  if (-not (Test-Path $src)) { return $false }
  New-Item -ItemType Directory -Force -Path $destDir | Out-Null
  Copy-Item -Force $src $dest
  $len = (Get-Item $dest).Length
  Write-Host ""
  Write-Host "SUCCESS: google-services.json installed ($len bytes)"
  Write-Host "From: $src"
  Write-Host "To:   $dest"
  # Marqueur pour l'agent
  Set-Content -Path (Join-Path $destDir "google-services.INSTALLED.txt") -Value ((Get-Date).ToString("o"))
  return $true
}

# Déjà présent ?
if (Test-Path $dest) {
  Write-Host "Already present at destination."
  exit 0
}

$deadline = (Get-Date).AddHours(2)
while ((Get-Date) -lt $deadline) {
  foreach ($dir in $watchDirs) {
    if (-not (Test-Path $dir)) { continue }
    $hits = Get-ChildItem -Path $dir -Filter "google-services*.json" -File -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending
    foreach ($f in $hits) {
      if (Try-Install $f.FullName) { exit 0 }
    }
  }
  Start-Sleep -Seconds 3
}

Write-Host "TIMEOUT: fichier non trouvé en 2h."
exit 1
