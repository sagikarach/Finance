import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';
import 'package:url_launcher/url_launcher.dart';

import '../services/update_service.dart';

/// Check for a new mobile release and, if found, prompt to download + install.
///
/// [silent] = true (startup auto-check): stay quiet when up-to-date or on error.
/// [silent] = false (user tapped "check for updates"): always give feedback.
Future<void> checkAndPromptUpdate(
  BuildContext context, {
  bool silent = false,
  UpdateService service = const UpdateService(),
}) async {
  UpdateInfo? info;
  try {
    info = await service.checkForUpdate();
  } catch (e) {
    if (!silent && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('בדיקת עדכון נכשלה: $e')),
      );
    }
    return;
  }
  if (!context.mounted) return;
  if (info == null) {
    if (!silent) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('האפליקציה מעודכנת.')),
      );
    }
    return;
  }
  await showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (_) => _UpdateDialog(info: info!, service: service),
  );
}

class _UpdateDialog extends StatefulWidget {
  final UpdateInfo info;
  final UpdateService service;

  const _UpdateDialog({required this.info, required this.service});

  @override
  State<_UpdateDialog> createState() => _UpdateDialogState();
}

class _UpdateDialogState extends State<_UpdateDialog> {
  double _progress = 0.0;
  bool _busy = false;
  String? _error;

  bool get _canInstall => Platform.isAndroid && widget.info.apkUrl != null;

  Future<void> _downloadAndInstall() async {
    setState(() {
      _busy = true;
      _error = null;
      _progress = 0.0;
    });
    try {
      final file = await widget.service.downloadApk(
        widget.info.apkUrl!,
        onProgress: (p) {
          if (mounted) setState(() => _progress = p);
        },
      );
      // Hand the APK to the system package installer (shows the OS prompt;
      // requires "install unknown apps" permission for this app).
      final res = await OpenFilex.open(
        file.path,
        type: 'application/vnd.android.package-archive',
      );
      if (res.type != ResultType.done) {
        throw Exception(res.message);
      }
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = 'ההתקנה נכשלה: $e';
        });
      }
    }
  }

  Future<void> _openReleasePage() async {
    final uri = Uri.tryParse(widget.info.releaseUrl);
    if (uri != null) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final notes = widget.info.notes.trim();
    return AlertDialog(
      title: Text('עדכון זמין — גרסה ${widget.info.version}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (notes.isNotEmpty) Text(notes),
            if (!_canInstall)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'לא ניתן להתקין ישירות במכשיר זה — ייפתח דף הגרסה להורדה.',
                ),
              ),
            if (_busy) ...[
              const SizedBox(height: 16),
              LinearProgressIndicator(
                value: _progress > 0 ? _progress : null,
              ),
              const SizedBox(height: 6),
              Text('מוריד… ${(_progress * 100).toStringAsFixed(0)}%'),
            ],
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: Colors.red)),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(),
          child: const Text('אחר כך'),
        ),
        FilledButton(
          onPressed: _busy
              ? null
              : (_canInstall ? _downloadAndInstall : _openReleasePage),
          child: Text(_canInstall ? 'הורד והתקן' : 'פתח דף הורדה'),
        ),
      ],
    );
  }
}
