package net.institutkalunga.parents

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * Notifications système natives (canal + son + logo école).
 */
class MainActivity : FlutterActivity() {
    companion object {
        private const val CHANNEL = "net.institutkalunga.parents/alerts"
    }

    override fun onStart() {
        super.onStart()
        KalungaParentsApplication.isInForeground = true
    }

    override fun onStop() {
        KalungaParentsApplication.isInForeground = false
        super.onStop()
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "ensureChannel" -> {
                        NotificationBranding.ensureChannel(this)
                        result.success(true)
                    }
                    "areNotificationsEnabled" -> {
                        result.success(
                            androidx.core.app.NotificationManagerCompat
                                .from(this)
                                .areNotificationsEnabled()
                        )
                    }
                    "showAlert" -> {
                        val title = call.argument<String>("title") ?: "ELIMU Go"
                        val body = call.argument<String>("body") ?: ""
                        result.success(NotificationBranding.show(this, title, body))
                    }
                    else -> result.notImplemented()
                }
            }
        NotificationBranding.ensureChannel(this)
    }
}
