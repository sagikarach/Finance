import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../models/movement.dart';
import '../services/bootstrap_service.dart';
import '../services/movements_service.dart';
import '../services/action_history_service.dart';
import '../services/session_service.dart';
import 'new_movement_screen.dart';
import 'workspace_screen.dart';

class MovementsScreen extends StatefulWidget {
  final String workspaceId;

  const MovementsScreen({super.key, required this.workspaceId});

  @override
  State<MovementsScreen> createState() => _MovementsScreenState();
}

class _MovementsScreenState extends State<MovementsScreen> {
  bool _syncing = false;
  bool _loading = true;
  String? _error;
  List<Movement> _items = <Movement>[];

  final SessionService _session = const SessionService();
  late final MovementsService _movements;
  late final ActionHistoryService _actions;
  late final BootstrapService _bootstrap;

  Future<void> _deleteMovement(Movement m) async {
    try {
      await _movements.tombstoneDelete(movementId: m.id);
      await _actions.logDeleteMovement(m: m);
      if (!mounted) return;
      setState(() => _items = _items.where((x) => x.id != m.id).toList());
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('התנועה נמחקה')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('שגיאת מחיקה: $e')),
      );
    }
  }

  @override
  void initState() {
    super.initState();
    _movements = MovementsService(workspaceId: widget.workspaceId);
    _actions = ActionHistoryService(workspaceId: widget.workspaceId);
    _bootstrap = BootstrapService(workspaceId: widget.workspaceId);
    _pullFromServer(showToast: false);
  }

  Future<void> _pullFromServer({required bool showToast}) async {
    if (!_session.isLoggedIn) return;

    setState(() {
      _syncing = true;
      _loading = true;
      _error = null;
    });
    try {
      await _bootstrap.ensureWorkspaceMeta();
      final items = await _movements.fetch(source: Source.server);

      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
      if (showToast) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('סונכרן בהצלחה')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
      if (showToast) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('שגיאת סנכרון: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_session.isLoggedIn) {
      return const Scaffold(body: Center(child: Text('לא מחובר')));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('תנועות'),
        actions: [
          IconButton(
            tooltip: 'שיתוף',
            onPressed: () async {
              final picked = await Navigator.of(context).push<String?>(
                MaterialPageRoute(builder: (_) => const WorkspaceScreen()),
              );
              if (picked == null) return;
              if (!context.mounted) return;
              Navigator.of(context).pushReplacement(
                MaterialPageRoute(
                  builder: (_) => MovementsScreen(workspaceId: picked),
                ),
              );
            },
            icon: const Icon(Icons.group),
          ),
          IconButton(
            onPressed: _syncing
                ? null
                : () => _pullFromServer(showToast: true),
            icon: _syncing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.sync),
            tooltip: 'סנכרן עכשיו',
          ),
          IconButton(
            onPressed: () => _session.signOut(),
            icon: const Icon(Icons.logout),
            tooltip: 'התנתק',
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => NewMovementScreen(workspaceId: widget.workspaceId),
          ),
        ),
        child: const Icon(Icons.add),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : (_error != null)
              ? Center(child: Text('שגיאה: $_error'))
              : (_items.isEmpty)
                  ? const Center(child: Text('אין תנועות עדיין'))
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: _items.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 10),
                      itemBuilder: (context, idx) {
                        final m = _items[idx];
                        final isIncome = m.amount > 0;
                        final amountAbs = m.amount.abs().toStringAsFixed(2);
                        final typeLabel = switch (m.type) {
                          'MONTHLY' => 'חודשי',
                          'YEARLY' => 'שנתי',
                          _ => 'חד פעמי',
                        };
                        return Dismissible(
                          key: ValueKey<String>(m.id),
                          direction: DismissDirection.endToStart,
                          confirmDismiss: (_) async {
                            return await showDialog<bool>(
                                  context: context,
                                  builder: (ctx) => AlertDialog(
                                    title: const Text('מחיקת תנועה'),
                                    content: const Text('האם למחוק את התנועה הזו?'),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.of(ctx).pop(false),
                                        child: const Text('ביטול'),
                                      ),
                                      ElevatedButton(
                                        onPressed: () => Navigator.of(ctx).pop(true),
                                        child: const Text('מחק'),
                                      ),
                                    ],
                                  ),
                                ) ??
                                false;
                          },
                          onDismissed: (_) => _deleteMovement(m),
                          background: Container(
                            alignment: Alignment.centerRight,
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            color: Colors.red.withValues(alpha: 0.12),
                            child: const Icon(Icons.delete_outline, color: Colors.red),
                          ),
                          child: Card(
                            child: ListTile(
                              title: Text('${m.category} • ${m.accountName}'),
                              subtitle: Text('${m.date} • $typeLabel'),
                              trailing: Text(
                                '${isIncome ? '+' : '-'}$amountAbs',
                                style: TextStyle(
                                  color: isIncome ? Colors.green : Colors.red,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                          ),
                        );
                      },
                    ),
    );
  }
}


