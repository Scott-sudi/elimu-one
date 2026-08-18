# Notifications push — Institut Kalunga Parents

## Deux modes

| Situation | Comment ça marche | État |
|-----------|-------------------|------|
| **App ouverte** | Notification système Android native + son | OK (apk récent) |
| **App fermée / téléphone verrouillé** | **Firebase Cloud Messaging (FCM)** — comme WhatsApp | **À activer une fois** (ci-dessous) |

Sans Firebase, le téléphone **ne peut pas** être réveillé si l’app est fermée.
Ce n’est pas un « serveur dans le téléphone » : c’est Google qui pousse le message.

## Activer le push app fermée (une seule fois)

### 1. Firebase (toi — 10 min)
1. Va sur https://console.firebase.google.com
2. Crée / ouvre le projet **Institut Kalunga**
3. Ajoute une app **Android**
   - Package name : `net.institutkalunga.parents`
4. Télécharge **`google-services.json`**
5. Place-le ici :
   `mobile/kalunga_parents/android/app/google-services.json`
6. Dans Firebase → Project settings → Cloud Messaging :
   - copie la **Server key** (ou crée une clé API Cloud Messaging)

### 2. Serveur o2switch
Dans le fichier `.env` du backend :
```
FCM_SERVER_KEY=ta_cle_serveur_firebase
```
Puis dans le Terminal cPanel :
```bash
cd ~/kalunga-school/backend && mkdir -p tmp && touch tmp/restart.txt
```

### 3. Rebuild APK
Après avoir mis `google-services.json` dans le projet, republier l’APK
(GitHub Actions ou `flutter build apk --release`).

Réinstalle l’APK, ouvre l’app **une fois** (pour enregistrer le jeton FCM),
puis ferme-la complètement et teste un message secrétariat / paiement / présence.

## Déjà branché côté serveur
- Message secrétariat publié → push FCM
- Présence / retard → push FCM
- Paiement enregistré → push FCM

## Canal Android
`kalunga_parents_alerts_v8` — Alertes Institut Kalunga (icône statut « IK »)
