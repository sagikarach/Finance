import 'package:flutter/material.dart';

import '../models/movement.dart';
import '../services/notifications_service.dart';

Future<void> showNotificationsSheet({
  required BuildContext context,
  required String workspaceId,
}) async {
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => _NotificationsSheet(workspaceId: workspaceId),
  );
}

class _NotificationsSheet extends StatefulWidget {
  final String workspaceId;

  const _NotificationsSheet({required this.workspaceId});

  @override
  State<_NotificationsSheet> createState() => _NotificationsSheetState();
}

class _NotificationsSheetState extends State<_NotificationsSheet> {
  bool _loading = true;
  String? _error;
  List<AppNotification> _items = <AppNotification>[];
  late final NotificationsService _svc;

  @override
  void initState() {
    super.initState();
    _svc = NotificationsService(workspaceId: widget.workspaceId);
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await _svc.fetchUnresolved();
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  Future<void> _openDetails(AppNotification n) async {
    Movement? m;
    try {
      m = await _svc.fetchMovementForDetails(n);
    } catch (_) {}

    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(n.title.trim().isEmpty ? 'התראה' : n.title),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (n.message.trim().isNotEmpty) Text(n.message),
              if (n.createdAt.trim().isNotEmpty) ...[
                const SizedBox(height: 12),
                Text('תאריך: ${n.createdAt}', textAlign: TextAlign.center),
              ],
              if (m != null) ...[
                const SizedBox(height: 16),
                const Text(
                  'פרטי תנועה',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                _kv('חשבון', m.accountName),
                _kv('קטגוריה', m.category),
                _kv('תאריך', m.date),
                _kv('סכום', m.amount.toStringAsFixed(2)),
                if ((m.description ?? '').trim().isNotEmpty)
                  _kv('תיאור', (m.description ?? '').trim()),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('סגור'),
          ),
        ],
      ),
    );
  }

  Widget _kv(String k, String v) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Text('$k: $v', textAlign: TextAlign.center),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'התראות',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              )
            else if (_error != null)
              Padding(
                padding: const EdgeInsets.all(12),
                child: Text(
                  'שגיאה: $_error',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.red),
                ),
              )
            else if (_items.isEmpty)
              const Padding(
                padding: EdgeInsets.all(16),
                child: Text('אין התראות לא פתורות', textAlign: TextAlign.center),
              )
            else
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: _items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, i) {
                    final n = _items[i];
                    return Card(
                      child: ListTile(
                        onTap: () => _openDetails(n),
                        title: Text(
                          n.title.trim().isEmpty ? 'התראה' : n.title,
                          textAlign: TextAlign.center,
                        ),
                        subtitle: n.message.trim().isEmpty
                            ? null
                            : Text(n.message, textAlign: TextAlign.center),
                      ),
                    );
                  },
                ),
              ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: _load,
                child: const Text('רענן'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}


