package net.institutkalunga.parents

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/**
 * Affiche une notification système quand l’app est en arrière-plan / fermée.
 * Si FCM envoie déjà un bloc `notification`, Android l’affiche tout seul :
 * on n’ajoute une notif locale que pour les messages data-only.
 */
class ElimuFirebaseMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        if (KalungaParentsApplication.isInForeground) return
        if (message.notification != null) return

        val title = message.data["title"]?.takeIf { it.isNotBlank() } ?: "ELIMU Go"
        val body = message.data["body"]?.takeIf { it.isNotBlank() }
            ?: "Vous avez une nouvelle notification."
        NotificationBranding.show(applicationContext, title, body)
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
    }
}
