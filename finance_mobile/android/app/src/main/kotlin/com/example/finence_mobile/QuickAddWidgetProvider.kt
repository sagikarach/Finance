package com.example.finance_mobile

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

class QuickAddWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        for (appWidgetId in appWidgetIds) {
            val views = RemoteViews(context.packageName, R.layout.quick_add_widget)

            val intent = Intent(context, MainActivity::class.java).apply {
                action = ACTION_ADD_MOVEMENT
                putExtra(EXTRA_TARGET, TARGET_ADD_MOVEMENT)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

            val pi = PendingIntent.getActivity(
                context,
                0,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            views.setOnClickPendingIntent(R.id.quick_add_widget_root, pi)
            appWidgetManager.updateAppWidget(appWidgetId, views)
        }
    }

    companion object {
        private const val EXTRA_TARGET = "launch_target"
        private const val TARGET_ADD_MOVEMENT = "add_movement"
        private const val ACTION_ADD_MOVEMENT = "com.example.finance_mobile.ADD_MOVEMENT"
    }
}


