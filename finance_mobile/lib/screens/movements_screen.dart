import 'dart:async';

import 'package:flutter/material.dart';

import '../models/movement.dart';
import '../services/bootstrap_service.dart';
import '../services/movements_service.dart';
import '../services/action_history_service.dart';
import '../services/session_service.dart';
import '../services/launch_target_service.dart';
import '../widgets/notifications_sheet.dart';
import '../widgets/header_actions_row.dart';
import 'account_switch_screen.dart';
import 'new_movement_screen.dart';
import 'savings_screen.dart';

class MovementsScreen extends StatefulWidget {
  final String workspaceId;
  final bool openAddMovementOnStart;

  const MovementsScreen({
    super.key,
    required this.workspaceId,
    this.openAddMovementOnStart = false,
  });

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
  StreamSubscription<String>? _launchSub;
  bool _openingAdd = false;

  Future<void> _openAddMovement() async {
    if (_openingAdd) return;
    _openingAdd = true;
    try {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => NewMovementScreen(workspaceId: widget.workspaceId),
        ),
      );
      if (!mounted) return;
      await _pullFromServer(showToast: false);
    } finally {
      _openingAdd = false;
    }
  }

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
    // Kick off network/pull work after first frame to avoid blocking initial render.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
    _pullFromServer(showToast: false);
    });

    _launchSub = LaunchTargetService.instance.targets.listen((t) {
      if (!mounted) return;
      if (t == 'add_movement') {
        _openAddMovement();
      }
    });
    if (widget.openAddMovementOnStart) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _openAddMovement());
    }
  }

  @override
  void dispose() {
    _launchSub?.cancel();
    super.dispose();
  }

  Future<void> _pullFromServer({required bool showToast}) async {
    if (!_session.isLoggedIn) return;
    if (!mounted) return;

    setState(() {
      _syncing = true;
      _loading = true;
      _error = null;
    });
    try {
      await _bootstrap.ensureWorkspaceMeta();
      final items = await _movements.fetchIncremental();

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
        title: HeaderActionsRow(
          title: 'תנועות',
          actions: [
            HeaderAction(
              icon: Icons.notifications_none,
              tooltip: 'התראות',
              onPressed: () => showNotificationsSheet(
                context: context,
                workspaceId: widget.workspaceId,
              ),
            ),
            HeaderAction(
              icon: Icons.group,
              tooltip: 'חשבונות',
              onPressed: () async {
                await Navigator.of(context).push<void>(
                  MaterialPageRoute(
                      builder: (_) => const AccountSwitchScreen()),
                );
              },
            ),
            HeaderAction(
              icon: Icons.savings,
              tooltip: 'חסכונות',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) =>
                      SavingsScreen(workspaceId: widget.workspaceId),
                ),
              ),
            ),
            HeaderAction(
              icon: Icons.sync,
              tooltip: 'סנכרן עכשיו',
              onPressed:
                  _syncing ? null : () => _pullFromServer(showToast: true),
            ),
            HeaderAction(
              icon: Icons.logout,
              tooltip: 'התנתק',
              onPressed: () => _session.signOut(),
            ),
          ],
        ),
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
                        final desc = (m.description ?? '').trim();
                        final titleText = desc.isNotEmpty ? desc : m.category;
                        final detailsParts = <String>[
                          m.date.trim(),
                          m.accountName.trim(),
                          m.category.trim(),
                          typeLabel.trim(),
                        ].where((s) => s.isNotEmpty).toList();
                        return Dismissible(
                          key: ValueKey<String>(m.id),
                          direction: DismissDirection.endToStart,
                          confirmDismiss: (_) async {
                            return await showDialog<bool>(
                                  context: context,
                                  builder: (ctx) => AlertDialog(
                                    title: const Text('מחיקת תנועה'),
                                    content:
                                        const Text('האם למחוק את התנועה הזו?'),
                                    actions: [
                                      TextButton(
                                        onPressed: () =>
                                            Navigator.of(ctx).pop(false),
                                        child: const Text('ביטול'),
                                      ),
                                      ElevatedButton(
                                        onPressed: () =>
                                            Navigator.of(ctx).pop(true),
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
                            child: const Icon(Icons.delete_outline,
                                color: Colors.red),
                          ),
                          child: Card(
                            elevation: 0,
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 14, vertical: 12),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          titleText,
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(
                                            fontSize: 16,
                                            fontWeight: FontWeight.w800,
                                          ),
                                        ),
                                        const SizedBox(height: 6),
                                        Text(
                                          detailsParts.join(' • '),
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(
                                            fontSize: 13,
                                            color: Theme.of(context)
                                                .textTheme
                                                .bodySmall
                                                ?.color
                                                ?.withValues(alpha: 0.8),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Text(
                                    '${isIncome ? '+' : '-'}$amountAbs',
                                    style: TextStyle(
                                      fontSize: 16,
                                      color:
                                          isIncome ? Colors.green : Colors.red,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    ),
    );
  }
}
