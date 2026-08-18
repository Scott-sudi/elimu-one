# Déploiement iOS (iPhone) — Institut Kalunga Parents

Préparé pour que le passage Mac → IPA / TestFlight soit simple.
**Même code Flutter** que l’APK Android.

## Déjà en place dans le projet

| Élément | Valeur |
|--------|--------|
| Bundle ID | `net.institutkalunga.parents` (aligné Android) |
| Nom affiché | Institut Kalunga |
| Permissions | Caméra, galerie |
| Background | `remote-notification` (prêt push) |
| Export encryption | `ITSAppUsesNonExemptEncryption = false` |
| Export options | `ios/ExportOptions-AppStore.plist`, `ios/ExportOptions-AdHoc.plist` |
| Script Mac | `scripts/build_ios_ipa.sh` |

## Ce dont tu auras besoin (une seule fois)

1. **Mac** avec **Xcode** (App Store) + outils ligne de commande  
2. Compte **[Apple Developer](https://developer.apple.com)** (~99 USD/an)  
3. Noter ton **Team ID** (developer.apple.com → Membership → Team ID)  
4. (Optionnel push app fermée) Projet **Firebase** + app iOS + `GoogleService-Info.plist`

## Jour J sur le Mac (checklist courte)

```bash
# 1. Copier le dossier mobile/kalunga_parents sur le Mac
cd kalunga_parents

# 2. Flutter installé + `flutter doctor` OK (Xcode coché)

# 3. Ouvrir une fois le projet pour le signing automatique :
open ios/Runner.xcworkspace
# → Runner → Signing & Capabilities
# → Team = ton équipe Apple
# → Bundle Identifier = net.institutkalunga.parents

# 4. Build IPA App Store / TestFlight
chmod +x scripts/build_ios_ipa.sh
TEAM_ID=TON_TEAM_ID ./scripts/build_ios_ipa.sh appstore

# ou Ad Hoc (appareils enregistrés) :
# TEAM_ID=TON_TEAM_ID ./scripts/build_ios_ipa.sh adhoc
```

L’IPA sort dans `build/ios/ipa/`.

## Publier

1. **TestFlight** (recommandé pour les parents tests)  
   - Xcode Organizer ou app **Transporter** → upload  
   - App Store Connect → TestFlight → inviter testeurs  
2. **App Store** (public)  
   - Fiche app, captures, confidentialité, soumission review  

## Firebase iOS (plus tard, push fermé)

1. Firebase Console → Add iOS app → Bundle `net.institutkalunga.parents`  
2. Télécharger `GoogleService-Info.plist` → `ios/Runner/`  
3. Activer APNs (clé .p8 Apple → Firebase Cloud Messaging)  
4. Sur o2switch : `FCM_SERVER_KEY` (déjà prévu côté Android)  

Sans Firebase, l’app iOS fonctionne (API + refresh ~25 s + son en foreground comme prévu).

## Pièges à éviter

- Ne **pas** builder l’IPA sous Windows  
- Ne pas laisser `com.example…` (déjà corrigé)  
- Sur Xcode, cocher **Automatically manage signing**  
- Version = `pubspec.yaml` (`1.1.0+4` aujourd’hui) : incrémenter `+N` à chaque upload TestFlight  

## Android vs iOS (rappel)

| | Android | iOS |
|--|---------|-----|
| ID | `net.institutkalunga.parents` | idem |
| Fichier | APK / AAB | IPA |
| Machine | Windows OK | **Mac obligatoire** |
| Tests | APK direct | TestFlight (ou Ad Hoc) |
