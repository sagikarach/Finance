import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../models/movement.dart';
import '../services/action_history_service.dart';
import '../services/bootstrap_service.dart';
import '../services/dashboard_meta_service.dart';
import '../services/movements_service.dart';
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
  late final MovementsService _movements;

  List<Movement> _items = <Movement>[];
  List<WorkspaceAction> _actionItems = <WorkspaceAction>[];
  final Map<String, Movement?> _movementDetailsById = <String, Movement?>{};
  final Map<String, Future<Movement?>> _movementFetches = <String, Future<Movement?>>{};

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
    _movements = MovementsService(workspaceId: widget.workspaceId);

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

  (Color, Color) _stripeGradientForAction(WorkspaceAction a, Brightness b) {
    // Palette inspired by desktop action history.
    // Right-side colored panel (RTL) with a subtle vertical gradient.
    Color base = switch (a.actionName) {
      'add_income_movement' => const Color(0xFF2E7D32), // green
      'add_outcome_movement' => const Color(0xFFC62828), // red
      'delete_movement' => const Color(0xFFB71C1C), // deep red
      'edit_saving' => const Color(0xFF1565C0), // blue
      _ => const Color(0xFF6A1B9A), // purple
    };

    if (b == Brightness.dark) {
      base = Color.lerp(base, Colors.white, 0.06) ?? base;
    } else {
      base = Color.lerp(base, Colors.black, 0.04) ?? base;
    }

    final top = Color.lerp(base, Colors.white, b == Brightness.dark ? 0.10 : 0.22) ?? base;
    final bottom = Color.lerp(base, Colors.black, b == Brightness.dark ? 0.18 : 0.10) ?? base;
    return (top, bottom);
  }

  String _actionLabel(WorkspaceAction a) {
    return switch (a.actionName) {
      'add_income_movement' => 'נוספה הכנסה',
      'add_outcome_movement' => 'נוספה הוצאה',
      'delete_movement' => 'נמחקה תנועה',
      'upload_outcome_file' => 'ייבוא קובץ הוצאות',
      'add_savings_account' => 'הוספת חשבון חיסכון',
      'add_one_time_event' => 'יצירת אירוע חד־פעמי',
      'edit_saving' => 'עודכן חסכון',
      'set_starter_amount' => 'הגדרת סכום התחלתי',
      'edit_installment_plan' => 'עריכת תשלומים',
      'edit_one_time_event' => 'עריכת אירוע חד־פעמי',
      'assign_movement_to_one_time_event' => 'שיוך תנועה לאירוע',
      'asign_movment_to_one_time_event' => 'שיוך תנועה לאירוע',
      'assign_movment_to_one_time_event' => 'שיוך תנועה לאירוע',
      _ => a.actionName.isEmpty ? 'פעולה' : a.actionName,
    };
  }

  String _fmtMoneySigned(num v) {
    final d = v.toDouble();
    final abs = d.abs();
    final s = _fmtMoney(abs);
    return d < 0 ? '-$s' : s;
  }

  String _fmtBudget(num v) => 'תקציב ${_fmtMoney(v.toDouble())}';

  String _movementSummary(Movement m) {
    final parts = <String>[];
    final date = m.date.trim();
    final acc = m.accountName.trim();
    final cat = m.category.trim();
    if (date.isNotEmpty) parts.add(date);
    if (acc.isNotEmpty) parts.add(acc);
    parts.add(_fmtMoneySigned(m.amount));
    if (cat.isNotEmpty) parts.add(cat);
    final d = (m.description ?? '').trim();
    if (d.isNotEmpty) parts.add(d);
    return parts.join(' • ');
  }

  String? _extractMovementIdForAction(WorkspaceAction a) {
    final m = a.action;
    final id1 = (m['movement_id'] as String?)?.trim();
    if (id1 != null && id1.isNotEmpty) return id1;
    // Some buggy writers used "movment_id".
    final id2 = (m['movment_id'] as String?)?.trim();
    if (id2 != null && id2.isNotEmpty) return id2;
    return null;
  }

  String _actionSubtitle(WorkspaceAction a) {
    final ts = a.timestamp.trim();
    final m = a.action;
    final amount = m['amount'];
    final acc = (m['account_name'] as String?)?.trim();
    final category = (m['category'] as String?)?.trim();
    final desc = (m['description'] as String?)?.trim();
    final movementId = _extractMovementIdForAction(a);

    // Desktop-parity formatting for a few important action types.
    if (a.actionName == 'upload_outcome_file') {
      final fileName = (m['file_name'] as String?)?.trim();
      final cnt = m['expenses_count'];
      final total = m['total_amount'];
      final parts = <String>[];
      if (ts.isNotEmpty) parts.add(ts);
      if (fileName != null && fileName.isNotEmpty) parts.add(fileName);
      if (cnt is num) parts.add('${cnt.toInt()} שורות');
      if (total is num) parts.add('סה״כ ${_fmtMoney(total.toDouble())}');
      return parts.join(' • ');
    }

    if (a.actionName == 'set_starter_amount') {
      final starter = m['starter_amount'];
      final parts = <String>[];
      if ((acc ?? '').isNotEmpty) parts.add(acc!);
      if (starter is num) parts.add(_fmtMoney(starter.toDouble()));
      return parts.isEmpty ? (ts.isNotEmpty ? ts : '') : ([if (ts.isNotEmpty) ts, ...parts].join(' • '));
    }

    if (a.actionName == 'edit_installment_plan') {
      final name = (m['plan_name'] as String?)?.trim() ?? '';
      final newName = (m['new_name'] as String?)?.trim() ?? '';
      final body = (name.isNotEmpty && newName.isNotEmpty && newName != name)
          ? '$name → $newName'
          : (name.isNotEmpty ? name : 'תשלומים');
      return ts.isNotEmpty ? '$ts • $body' : body;
    }

    if (a.actionName == 'edit_one_time_event') {
      final name = (m['event_name'] as String?)?.trim() ?? '';
      final budget = m['budget'];
      final parts = <String>[];
      if (name.isNotEmpty) parts.add(name);
      if (budget is num && budget.toDouble() != 0.0) parts.add(_fmtBudget(budget));
      final body = parts.isEmpty ? 'אירוע' : parts.join(' • ');
      return ts.isNotEmpty ? '$ts • $body' : body;
    }

    if (a.actionName == 'assign_movement_to_one_time_event' ||
        a.actionName == 'asign_movment_to_one_time_event' ||
        a.actionName == 'assign_movment_to_one_time_event') {
      final eventName = (m['event_name'] as String?)?.trim();
      final eventId = (m['event_id'] as String?)?.trim();
      final parts = <String>[];
      if (ts.isNotEmpty) parts.add(ts);
      if (eventName != null && eventName.isNotEmpty) {
        parts.add(eventName);
      } else if (eventId != null && eventId.isNotEmpty) {
        // If we don't have the name, show a generic label (avoid raw ids).
        parts.add('אירוע');
      }

      // Prefer movement details (from cache/backfill). Never show raw movement id.
      if (movementId != null && movementId.isNotEmpty) {
        final cached = _movementDetailsById[movementId];
        if (cached != null) {
          parts.add(_movementSummary(cached));
        } else if (_movementDetailsById.containsKey(movementId)) {
          parts.add('לא נמצאו פרטי תנועה');
        } else {
          parts.add('טוען פרטי תנועה...');
        }
      }

      return parts.join(' • ');
    }

    final parts = <String>[];
    if (ts.isNotEmpty) parts.add(ts);
    if (acc != null && acc.isNotEmpty) parts.add(acc);
    if (amount is num) parts.add(_fmtMoney(amount.toDouble()));
    if (category != null && category.isNotEmpty) parts.add(category);
    if (desc != null && desc.isNotEmpty) parts.add(desc);

    // If this is an "add movement" action and we don't have the movement details yet,
    // try to pull the movement doc (by id) and show the actual movement instead of the id.
    final isAddMovement = a.actionName == 'add_income_movement' || a.actionName == 'add_outcome_movement';
    if (isAddMovement &&
        (acc == null || acc.isEmpty) &&
        amount is! num &&
        (movementId ?? '').isNotEmpty) {
      final cached = _movementDetailsById[movementId];
      if (cached != null) {
        parts.add(_movementSummary(cached));
      } else if (_movementDetailsById.containsKey(movementId)) {
        // We tried and couldn't fetch it; show a friendly fallback (never show raw id).
        parts.add('לא נמצאו פרטים לתנועה');
      }
    }

    return parts.join(' • ');
  }

  bool _needsMovementBackfill(WorkspaceAction a) {
    final isMovementRelated =
        a.actionName == 'add_income_movement' ||
        a.actionName == 'add_outcome_movement' ||
        a.actionName == 'assign_movement_to_one_time_event' ||
        a.actionName == 'asign_movment_to_one_time_event' ||
        a.actionName == 'assign_movment_to_one_time_event';
    if (!isMovementRelated) return false;
    final m = a.action;
    final movementId = _extractMovementIdForAction(a) ?? '';
    if (movementId.isEmpty) return false;
    // If the action already has rich details, no need to backfill.
    final hasAnyDetail =
        (m['account_name'] as String?)?.trim().isNotEmpty == true ||
        (m['category'] as String?)?.trim().isNotEmpty == true ||
        (m['amount'] is num);
    if (hasAnyDetail) return false;
    return !_movementDetailsById.containsKey(movementId) && !_movementFetches.containsKey(movementId);
  }

  void _ensureMovementBackfill(WorkspaceAction a) {
    if (!_needsMovementBackfill(a)) return;
    final movementId = (_extractMovementIdForAction(a) ?? '').trim();
    if (movementId.isEmpty) return;
    final fut = FirebaseFirestore.instance
        .collection('workspaces')
        .doc(widget.workspaceId)
        .collection('movements')
        .doc(movementId)
        .get(const GetOptions(source: Source.server))
        .then((snap) {
      final data = snap.data();
      if (data == null) return null;
      final m = Movement.fromFirestore(data);
      return m.id.trim().isEmpty ? null : m;
    }).catchError((_) => null);

    _movementFetches[movementId] = fut;
    fut.then((m) {
      _movementFetches.remove(movementId);
      // Store null as "fetched but missing", to avoid refetch loops.
      _movementDetailsById[movementId] = m;
      if (mounted) setState(() {});
    });
  }

  Widget _actionHistoryCard(WorkspaceAction a) {
    final b = Theme.of(context).brightness;
    final (top, bottom) = _stripeGradientForAction(a, b);
    const radius = 14.0;
    const stripeW = 14.0; // ~1/10 of a typical card width on mobile

    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(radius),
        ),
        // In a scrolling list the height constraints are unbounded; using a Row
        // with CrossAxisAlignment.stretch would try to stretch to infinity.
        // IntrinsicHeight makes the Row's height match its content, then the
        // colored panel can safely stretch to the card height.
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Content (RTL -> text starts on the right).
              Expanded(
                child: Padding(
                  padding: const EdgeInsetsDirectional.fromSTEB(14, 12, 12, 12),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _actionLabel(a),
                        textAlign: TextAlign.start,
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        _actionSubtitle(a),
                        textAlign: TextAlign.start,
                        style: TextStyle(
                          color: Theme.of(context).textTheme.bodySmall?.color,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              // Right-side colored panel (RTL design).
              SizedBox(
                width: stripeW,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [top, bottom],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
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
              : Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
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
                      const Text(
                        'היסטוריית פעולות',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 10),
                      Expanded(
                        child: _actionItems.isEmpty
                            ? const Center(child: Text('אין פעולות עדיין'))
                            : ListView.builder(
                                padding: const EdgeInsets.only(top: 8, left: 12, bottom: 12),
                                itemCount: _actionItems.length,
                                itemBuilder: (context, idx) {
                                  final a = _actionItems[idx];
                                  _ensureMovementBackfill(a);
                                  return Padding(
                                    padding: const EdgeInsets.only(bottom: 6),
                                    child: _actionHistoryCard(a),
                                  );
                                },
                              ),
                      ),
                    ],
                  ),
                ),
    );
  }
}
