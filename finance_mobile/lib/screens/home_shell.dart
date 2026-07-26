import 'dart:async';

import 'package:flutter/material.dart';

import '../services/launch_target_service.dart';
import '../services/session_service.dart';
import '../theme/app_colors.dart';
import '../widgets/ui/app_bottom_nav.dart';
import '../widgets/update_prompt.dart';
import 'new_movement_screen.dart';
import 'tabs/assets_tab.dart';
import 'tabs/home_tab.dart';
import 'tabs/more_tab.dart';
import 'tabs/savings_tab.dart';
import 'tabs/transactions_tab.dart';

class HomeShell extends StatefulWidget {
  final String workspaceId;
  final bool openAddMovementOnStart;

  const HomeShell({
    super.key,
    required this.workspaceId,
    this.openAddMovementOnStart = false,
  });

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  final SessionService _session = const SessionService();

  /// Bumped whenever data changes (e.g. after adding a movement) so every tab
  /// re-pulls from the server.
  final ValueNotifier<int> _refresh = ValueNotifier<int>(0);

  int _index = 0;
  StreamSubscription<String>? _launchSub;
  bool _openingAdd = false;

  static const _navItems = [
    NavItem(Icons.home_rounded, 'בית'),
    NavItem(Icons.receipt_long_rounded, 'תנועות'),
    NavItem(Icons.savings_rounded, 'חסכונות'),
    NavItem(Icons.account_balance_rounded, 'נכסים'),
    NavItem(Icons.grid_view_rounded, 'עוד'),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      checkAndPromptUpdate(context, silent: true);
    });
    _launchSub = LaunchTargetService.instance.targets.listen((t) {
      if (!mounted) return;
      if (t == 'add_movement') openAdd();
    });
    if (widget.openAddMovementOnStart) {
      WidgetsBinding.instance.addPostFrameCallback((_) => openAdd());
    }
  }

  @override
  void dispose() {
    _launchSub?.cancel();
    _refresh.dispose();
    super.dispose();
  }

  Future<void> openAdd() async {
    if (_openingAdd) return;
    _openingAdd = true;
    try {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => NewMovementScreen(workspaceId: widget.workspaceId),
        ),
      );
      _refresh.value++;
    } finally {
      _openingAdd = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_session.isLoggedIn) {
      return const Scaffold(body: Center(child: Text('לא מחובר')));
    }

    final wid = widget.workspaceId;
    final tabs = <Widget>[
      HomeTab(
        workspaceId: wid,
        refresh: _refresh,
        onAdd: openAdd,
        onSeeTransactions: () => setState(() => _index = 1),
      ),
      TransactionsTab(workspaceId: wid, refresh: _refresh),
      SavingsTab(workspaceId: wid, refresh: _refresh),
      AssetsTab(workspaceId: wid, refresh: _refresh),
      MoreTab(workspaceId: wid, refresh: _refresh),
    ];

    return Scaffold(
      backgroundColor: AppColors.screen,
      body: IndexedStack(index: _index, children: tabs),
      // + button in the bottom-left corner (RTL end side).
      floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
      floatingActionButton: Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: FloatingActionButton(
          onPressed: openAdd,
          backgroundColor: AppColors.ink,
          foregroundColor: Colors.white,
          elevation: 4,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          child: const Icon(Icons.add_rounded, size: 28),
        ),
      ),
      bottomNavigationBar: AppBottomNav(
        items: _navItems,
        index: _index,
        onChanged: (i) => setState(() => _index = i),
      ),
    );
  }
}
