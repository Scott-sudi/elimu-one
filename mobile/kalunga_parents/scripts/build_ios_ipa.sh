#!/usr/bin/env bash
# Build IPA Institut Kalunga Parents — à lancer UNIQUEMENT sur un Mac.
# Usage :
#   ./scripts/build_ios_ipa.sh                  # App Store / TestFlight
#   ./scripts/build_ios_ipa.sh adhoc            # Ad Hoc
#   TEAM_ID=AB12CD34EF ./scripts/build_ios_ipa.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Erreur: ce script doit tourner sur macOS (Xcode requis)."
  exit 1
fi

if ! command -v flutter >/dev/null 2>&1; then
  echo "Erreur: Flutter introuvable dans le PATH."
  exit 1
fi

if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "Erreur: Xcode / xcodebuild introuvable. Installe Xcode depuis l’App Store."
  exit 1
fi

MODE="${1:-appstore}"
TEAM_ID="${TEAM_ID:-}"

case "$MODE" in
  appstore|app-store|testflight)
    EXPORT_SRC="$ROOT/ios/ExportOptions-AppStore.plist"
    ;;
  adhoc|ad-hoc)
    EXPORT_SRC="$ROOT/ios/ExportOptions-AdHoc.plist"
    ;;
  *)
    echo "Usage: $0 [appstore|adhoc]"
    exit 1
    ;;
esac

EXPORT_OPTS="$ROOT/ios/.ExportOptions.generated.plist"
cp "$EXPORT_SRC" "$EXPORT_OPTS"

if [[ -n "$TEAM_ID" ]]; then
  /usr/bin/sed -i '' "s/TEAM_ID/${TEAM_ID}/g" "$EXPORT_OPTS"
elif grep -q "TEAM_ID" "$EXPORT_OPTS"; then
  echo "Astuce: exporte TEAM_ID=XXXXXXXXXX (Team ID Apple Developer)."
  echo "Sans TEAM_ID, Xcode peut quand même signer si le projet a un Development Team."
fi

echo "==> flutter pub get"
flutter pub get

echo "==> pod install"
cd ios
if command -v pod >/dev/null 2>&1; then
  pod install
else
  echo "CocoaPods manquant. Installe: sudo gem install cocoapods"
  exit 1
fi
cd "$ROOT"

echo "==> flutter build ipa"
flutter build ipa --release --export-options-plist="$EXPORT_OPTS"

IPA="$(ls -1t build/ios/ipa/*.ipa 2>/dev/null | head -1 || true)"
if [[ -n "${IPA:-}" ]]; then
  echo "OK IPA: $IPA"
else
  echo "Build terminé — vérifie build/ios/ipa/ ou l’archive Xcode."
fi

echo "Suite: Transporter / Xcode → TestFlight, ou distribute Ad Hoc."
