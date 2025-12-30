package com.example.finence_mobile

import android.content.Intent
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    companion object {
        private const val CHANNEL = "finence/launch"
        private const val EXTRA_TARGET = "launch_target"
        private const val TARGET_ADD_MOVEMENT = "add_movement"
        private const val ACTION_ADD_MOVEMENT = "com.example.finence_mobile.ADD_MOVEMENT"

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
