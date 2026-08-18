# Surveille le téléchargement de la clé compte de service Firebase
# (fichier type *-firebase-adminsdk-*.json) et le copie dans backend/secrets/

$ErrorActionPreference = "Continue"
$destDir = "C:\Users\Elisée\Desktop\IK\kalunga-school\backend\secrets"
$dest = Join-Path $destDir "firebase-adminsdk.json"
$watchDirs = @(
  "$env:USERPROFILE\Downloads",
  "$env:USERPROFILE\Téléchargements",
  "$env:USERPROFILE\Desktop",
  "$env:USERPROFILE\Bureau",
  "C:\Users\Elisée\Desktop",
  "C:\Users\Elisée\Downloads",
  "C:\Users\Elisée\Desktop\IK"
) | Select-Object -Unique

New-Item -ItemType Directory -Force -Path $destDir | Out-Null
Write-Host "Watching for firebase-adminsdk JSON ..."
Write-Host "Destination: $dest"

function Try-Install([string]$src) {
  if (-not (Test-Path $src)) { return $false }
  # Ne pas prendre google-services.json
  $name = [IO.Path]::GetFileName($src).ToLowerInvariant()
  if ($name -eq "google-services.json") { return $false }
  if ($name -notmatch "firebase|adminsdk|service.account|institut-kalunga") {
    # Accepte aussi tout JSON service account Google
    try {
      $raw = Get-Content -Raw $src
      if ($raw -notmatch '"type"\s*:\s*"service_account"') { return $false }
    } catch { return $false }
  }
  Copy-Item -Force $src $dest
  Write-Host "SUCCESS: service account installed from $src"
  Set-Content -Path (Join-Path $destDir "firebase-adminsdk.INSTALLED.txt") -Value ((Get-Date).ToString("o"))
  return $true
}

if (Test-Path $dest) {
  Write-Host "Already present."
  exit 0
}

$deadline = (Get-Date).AddHours(2)
while ((Get-Date) -lt $deadline) {
  foreach ($dir in $watchDirs) {
    if (-not (Test-Path $dir)) { continue }
    $hits = Get-ChildItem -Path $dir -Filter "*.json" -File -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match "firebase|adminsdk|institut-kalunga" -or $_.Length -lt 5000 } |
      Sort-Object LastWriteTime -Descending
    foreach ($f in $hits) {
      if (Try-Install $f.FullName) { exit 0 }
    }
    # Scan recent json with service_account type
    $recent = Get-ChildItem -Path $dir -Filter "*.json" -File -ErrorAction SilentlyContinue |
      Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-6) } |
      Sort-Object LastWriteTime -Descending
    foreach ($f in $recent) {
      if (Try-Install $f.FullName) { exit 0 }
    }
  }
  Start-Sleep -Seconds 4
}
Write-Host "TIMEOUT"
exit 1
