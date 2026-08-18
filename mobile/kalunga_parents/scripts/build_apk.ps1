# Build ELIMU Go APK (Windows)
param(
    [string]$ApiHost = "https://REMPLACER-PAR-VOTRE-DOMAINE-ELIMU"
)

$Flutter = Resolve-Path "..\..\..\tools\flutter\bin\flutter.bat" -ErrorAction SilentlyContinue
if (-not $Flutter) {
    $Flutter = "flutter"
}

Push-Location $PSScriptRoot\..
try {
    & $Flutter pub get
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $Flutter build apk --release --dart-define=ELIMU_API_HOST=$ApiHost
    Write-Host "APK: build\app\outputs\flutter-apk\app-release.apk"
} finally {
    Pop-Location
}
