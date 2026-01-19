package com.example.finance_mobile

import android.content.Intent
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.android.RenderMode
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

// FlutterFragmentActivity is required for local_auth (biometrics) on Android.
class MainActivity : FlutterFragmentActivity() {
    companion object {
        private const val CHANNEL = "finance/launch"
        private const val EXTRA_TARGET = "launch_target"
        private const val TARGET_ADD_MOVEMENT = "add_movement"
        private const val ACTION_ADD_MOVEMENT = "com.example.finance_mobile.ADD_MOVEMENT"

        private var pendingTarget: String? = null
        private var channel: MethodChannel? = null
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
        channel?.setMethodCallHandler { call, result ->
            when (call.method) {
                "getInitialTarget" -> {
                    val t = pendingTarget
                    pendingTarget = null
                    result.success(t)
                }
                else -> result.notImplemented()
            }
        }
        handleIntent(intent, notify = false)
    }

    // Workaround for some OEM GPU/SurfaceView issues (Adreno/Gralloc "Unknown Format"
    // / AHardwareBuffer allocation failures) that can cause the process to be killed
    // and Flutter to lose the debug connection.
    override fun getRenderMode(): RenderMode = RenderMode.texture

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent, notify = true)
    }

    private fun handleIntent(intent: Intent?, notify: Boolean) {
        if (intent == null) return
        val action = intent.action ?: ""
        val extra = intent.getStringExtra(EXTRA_TARGET) ?: ""
        val target = when {
            action == ACTION_ADD_MOVEMENT -> TARGET_ADD_MOVEMENT
            extra == TARGET_ADD_MOVEMENT -> TARGET_ADD_MOVEMENT
            else -> ""
        }
        if (target.isEmpty()) return
        pendingTarget = target
        if (notify) {
            try {
                channel?.invokeMethod("onTarget", target)
            } catch (_: Exception) {
            }
        }
    }
}
