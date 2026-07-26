import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../../models/movement.dart';
import '../../services/movements_service.dart';
import '../../services/session_service.dart';
import '../../theme/app_colors.dart';
import '../../widgets/ui/tab_top_bar.dart';
import '../../widgets/ui/tx_tile.dart';

class TransactionsTab extends StatefulWidget {
  final String workspaceId;
  final Listenable refresh;
  final VoidCallback onAdd;

  const TransactionsTab({
    super.key,
    required this.workspaceId,
    required this.refresh,
    required this.onAdd,
  });

  @override
  State<TransactionsTab> createState() => _TransactionsTabState();
}

class _TransactionsTabState extends State<TransactionsTab> {
  final SessionService _session = const SessionService();
  late final MovementsService _movements;

  bool _loading = true;
  bool _syncing = false;
  String? _error;
  List<Movement> _items = const [];

  @override
  void initState() {
    super.initState();
    _movements = MovementsService(workspaceId: widget.workspaceId);
    widget.refresh.addListener(_onRefresh);
    WidgetsBinding.instance
        .addPostFrameCallback((_) => _pull(showToast: false));
  }

  @override
  void dispose() {
    widget.refresh.removeListener(_onRefresh);
    super.dispose();
  }

  void _onRefresh() => _pull(showToast: false);

  Future<void> _pull({required bool showToast}) async {
    if (!_session.isLoggedIn || _syncing) return;
    setState(() {
      _syncing = true;
      _loading = _items.isEmpty;
      _error = null;
    });
    try {
      final items = await _movements.fetch(source: Source.server);
      items.sort((a, b) {
        final c = b.date.compareTo(a.date);
        if (c != 0) return c;
        return (b.updatedAtMs ?? 0).compareTo(a.updatedAtMs ?? 0);
      });
      if (!mounted) return;
      setState(() {
        _items = items;
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
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  Future<void> _confirmDelete(Movement m) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('מחיקת תנועה'),
        content: const Text('למחוק את התנועה?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('ביטול')),
          TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('מחק')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _movements.tombstoneDelete(movementId: m.id);
      await _pull(showToast: false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('התנועה נמחקה')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('שגיאה: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.screen,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            TabTopBar(
              title: 'תנועות',
              workspaceId: widget.workspaceId,
              syncing: _syncing,
              onSync: () => _pull(showToast: true),
              extraIcon: Icons.add_rounded,
              onExtra: widget.onAdd,
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(child: Text('שגיאה: $_error'))
                      : _items.isEmpty
                          ? const Center(child: Text('אין תנועות עדיין'))
                          : ListView.builder(
                              padding:
                                  const EdgeInsets.fromLTRB(16, 4, 16, 110),
                              itemCount: _items.length,
                              itemBuilder: (context, i) {
                                final m = _items[i];
                                return Dismissible(
                                  key: ValueKey(m.id),
                                  direction: DismissDirection.endToStart,
                                  confirmDismiss: (_) async {
                                    await _confirmDelete(m);
                                    return false;
                                  },
                                  background: _deleteBg(),
                                  child: TxTile(movement: m),
                                );
                              },
                            ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _deleteBg() {
    return Container(
      alignment: AlignmentDirectional.centerStart,
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 22),
      decoration: BoxDecoration(
        color: AppColors.clay.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(20),
      ),
      child: const Icon(Icons.delete_outline_rounded, color: AppColors.clay),
    );
  }
}
