package net.institutkalunga.parents

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.os.Build
import androidx.core.app.NotificationCompat

/**
 * Crée le canal de notification dès le démarrage du process
 * (y compris quand l’app est tuée et qu’un push FCM arrive).
 */
class KalungaParentsApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        instance = this
        ensureParentsAlertChannel()
    }

    private fun ensureParentsAlertChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val mgr = getSystemService(NotificationManager::class.java) ?: return
        val soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)
        val attrs = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_NOTIFICATION)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build()
        val channel = NotificationChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Messages école, présences, finances — avec son"
            enableVibration(true)
            vibrationPattern = longArrayOf(0, 500, 200, 500, 200, 500)
            setSound(soundUri, attrs)
            enableLights(true)
            setShowBadge(true)
            lockscreenVisibility = NotificationCompat.VISIBILITY_PUBLIC
        }
        mgr.createNotificationChannel(channel)
    }

    companion object {
        const val CHANNEL_ID = "elimu_go_alerts_v1"
        const val CHANNEL_NAME = "Alertes ELIMU Go"

        @Volatile
        var instance: KalungaParentsApplication? = null
            private set

        @Volatile
        var isInForeground: Boolean = false
    }
}
