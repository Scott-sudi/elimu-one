# Notifications push — ELIMU Go (app fermée)

Sans Firebase, le téléphone ne peut pas être réveillé si l’app est fermée.
Google (FCM) pousse le message, comme WhatsApp.

Package Android : `net.institutkalunga.parents`
API ELIMU One : `http://elimu.susc3383.odns.fr`

## 1. Créer le projet Firebase (compte Google)

1. Ouvrez https://console.firebase.google.com
2. Cliquez **Ajouter un projet**
3. Nom : `elimu-go`
4. Désactivez Google Analytics si proposé → **Créer le projet**
5. Cliquez l’icône **Android**
6. Nom du package : `net.institutkalunga.parents` (exactement)
7. Surnom : `ELIMU Go`
8. Téléchargez **google-services.json**
9. Placez-le dans :
   `mobile/kalunga_parents/android/app/google-services.json`

## 2. Clé privée (compte de service)

1. Firebase → ⚙️ **Paramètres du projet**
2. Onglet **Comptes de service**
3. **Générer une nouvelle clé privée** → un fichier JSON se télécharge
4. Ne le commitez jamais sur GitHub
5. Sur o2switch, copiez-le vers :
   `/home/susc3383/elimu-school/backend/secrets/firebase-adminsdk.json`

## 3. Serveur o2switch

Dans `~/elimu-school/.env` :

```
FCM_PROJECT_ID=elimu-go
FCM_SERVICE_ACCOUNT_FILE=secrets/firebase-adminsdk.json
```

Puis Terminal :

```sh
source /home/susc3383/virtualenv/elimu-school/backend/3.12/bin/activate
cd /home/susc3383/elimu-school/backend
pip install 'google-auth>=2.29'
python manage.py send_test_parent_push --help
touch tmp/restart.txt
```

## 4. APK

Rebuild après `google-services.json` :
GitHub Actions → **Build ELIMU Go APK**
`--dart-define=ELIMU_API_HOST=http://elimu.susc3383.odns.fr`

Réinstallez l’APK, ouvrez l’app **une fois** (jeton FCM), fermez-la, testez un message secrétariat.
