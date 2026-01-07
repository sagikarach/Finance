import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../models/movement.dart';
import '../services/action_history_service.dart';
import '../services/bootstrap_service.dart';
import '../services/dashboard_meta_service.dart';
import '../services/session_service.dart';
import '../services/launch_target_service.dart';
import 'account_switch_screen.dart';
import 'movements_screen.dart';
import 'new_movement_screen.dart';
import 'savings_screen.dart';
import '../widgets/notifications_sheet.dart';
import '../widgets/header_actions_row.dart';

class DashboardScreen extends StatefulWidget {
  final String workspaceId;
  final bool openAddMovementOnStart;

  const DashboardScreen({
    super.key,
    required this.workspaceId,
    this.openAddMovementOnStart = false,
  });

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _syncing = false;
  bool _loading = true;
  String? _error;

  final SessionService _session = const SessionService();
  late final BootstrapService _bootstrap;
  late final ActionHistoryService _actions;
  late final DashboardMetaService _dashboardMeta;

  List<Movement> _items = <Movement>[];
  List<WorkspaceAction> _actionItems = <WorkspaceAction>[];

  double _totalAll = 0.0;
  double _totalLiquid = 0.0;
  double? _avgMonthlyIncome;
  double? _avgMonthlyExpense;

  StreamSubscription<String>? _launchSub;
  bool _openingAdd = false;

  @override
  void initState() {
    super.initState();
    _bootstrap = BootstrapService(workspaceId: widget.workspaceId);
    _actions = ActionHistoryService(workspaceId: widget.workspaceId);
    _dashboardMeta = DashboardMetaService(workspaceId: widget.workspaceId);

    _pullFromServer(showToast: false);

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

  DateTime? _parseDate(String s) {
    final t = s.trim();
    if (t.isEmpty) return null;
    try {
      return DateTime.parse(t);
    } catch (_) {
      return null;
    }
  }

  String _monthKey(DateTime d) {
    final mm = d.month.toString().padLeft(2, '0');
    return '${d.year}-$mm';
  }

  String _prevMonthKey(DateTime now) {
    if (now.month == 1) return '${now.year - 1}-12';
    final mm = (now.month - 1).toString().padLeft(2, '0');
    return '${now.year}-$mm';
  }

  String _fmtMoney(double v) => '${v.toStringAsFixed(2)} ₪';

  String _actionLabel(WorkspaceAction a) {
    return switch (a.actionName) {
      'add_income_movement' => 'נוספה הכנסה',
      'add_outcome_movement' => 'נוספה הוצאה',
      'delete_movement' => 'נמחקה תנועה',
      'edit_saving' => 'עודכן חסכון',
      _ => a.actionName.isEmpty ? 'פעולה' : a.actionName,
    };
  }

  String _actionSubtitle(WorkspaceAction a) {
    final ts = a.timestamp.trim();
    final m = a.action;
    final amount = m['amount'];
    final acc = (m['account_name'] as String?)?.trim();
    final movementId = (m['movement_id'] as String?)?.trim();

    final parts = <String>[];
    if (ts.isNotEmpty) parts.add(ts);
    if (acc != null && acc.isNotEmpty) parts.add(acc);
    if (amount is num) parts.add(_fmtMoney(amount.toDouble()));
    if (movementId != null && movementId.isNotEmpty) parts.add(movementId);
    return parts.join(' • ');
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

      final dashboard = await _dashboardMeta.fetch(source: Source.server);
      final actions = await _actions.fetch(source: Source.server, limit: 60);
      final items = <Movement>[];

      if (!mounted) return;
      setState(() {
        _items = items;
        _actionItems = actions;
        _totalAll = dashboard?.totalAll ?? 0.0;
        _totalLiquid = dashboard?.totalLiquid ?? 0.0;
        _avgMonthlyIncome = dashboard?.avgMonthlyIncome;
        _avgMonthlyExpense = dashboard?.avgMonthlyExpense;
        _loading = false;
      });

      if (showToast && mounted) {
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

  Widget _statCard({
    required String title,
    required String value,
    IconData? icon,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              if (icon != null) ...[
                Icon(icon),
                const SizedBox(height: 8),
              ],
              Text(
                title,
                textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              Text(
                value,
                textAlign: TextAlign.center,
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!_session.isLoggedIn) {
      return const Scaffold(body: Center(child: Text('לא מחובר')));
    }

    return Scaffold(
      appBar: AppBar(
        title: HeaderActionsRow(
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
              icon: Icons.receipt_long,
              tooltip: 'תנועות',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) =>
                      MovementsScreen(workspaceId: widget.workspaceId),
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
        onPressed: _openAddMovement,
        child: const Icon(Icons.add),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : (_error != null)
              ? Center(child: Text('שגיאה: $_error'))
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _statCard(
                            title: 'סה״כ כסף',
                            value: _fmtMoney(_totalAll),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _statCard(
                            title: 'סה״כ כסף נזיל',
                            value: _fmtMoney(_totalLiquid),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: _statCard(
                            title: 'ממוצע הכנסות',
                            value: _avgMonthlyIncome == null
                                ? '—'
                                : _fmtMoney(_avgMonthlyIncome!),
                            icon: Icons.trending_up,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _statCard(
                            title: 'ממוצע הוצאות ',
                            value: _avgMonthlyExpense == null
                                ? '—'
                                : _fmtMoney(_avgMonthlyExpense!),
                            icon: Icons.trending_down,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    const Center(
                      child: Text(
                        'היסטוריית פעולות',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.w800),
                      ),
                    ),
                    const SizedBox(height: 8),
                    if (_actionItems.isEmpty)
                      const Center(child: Text('אין פעולות עדיין'))
                    else
                      ..._actionItems.map(
                        (a) => Card(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 14,
                              vertical: 12,
                            ),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.center,
                              children: [
                                Text(
                                  _actionLabel(a),
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w700),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  _actionSubtitle(a),
                                  textAlign: TextAlign.center,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    const SizedBox(height: 80),
                  ],
                ),
    );
  }
}
