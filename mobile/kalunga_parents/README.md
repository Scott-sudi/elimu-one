# Kalunga Parents (Flutter)

Application mobile officielle des **parents** de l’Institut Kalunga.

Elle consomme uniquement l’API REST Django déjà déployée — aucune base de données locale métier.

## API

| Élément | Valeur |
|--------|--------|
| Hôte actuel (o2switch) | `http://institut-kalunga.net.susc3383.odns.fr` |
| Préfixe API | `/api/v1` |
| Config | `lib/config/api_config.dart` |

## APK Android

À chaque push sur `main`, GitHub Actions construit une APK release :

1. Onglet **Actions** → workflow **Build Android APK**
2. Ou **Releases** → télécharger `app-release.apk`
3. Sur le téléphone : autoriser l’installation depuis des sources inconnues, puis ouvrir l’APK

## Lancer en local (web)

```bat
cd mobile\kalunga_parents
..\..\..\tools\flutter\bin\flutter.bat pub get
..\..\..\tools\flutter\bin\flutter.bat run -d edge --web-port=7357
```

Proxy CORS web : `python tool/dev_cors_proxy.py` (port 8788).
