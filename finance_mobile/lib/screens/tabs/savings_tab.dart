import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../../services/savings_service.dart';
import '../../services/session_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/money.dart';
import '../../widgets/ui/cards.dart';
import '../../widgets/ui/tab_top_bar.dart';
import '../savings_screen.dart';

class SavingsTab extends StatefulWidget {
  final String workspaceId;
  final Listenable refresh;
  const SavingsTab(
      {super.key, required this.workspaceId, required this.refresh});

  @override
  State<SavingsTab> createState() => _SavingsTabState();
}

class _SavingsTabState extends State<SavingsTab> {
  final SessionService _session = const SessionService();
  late final SavingsService _savings;

  bool _loading = true;
  bool _syncing = false;
  String? _error;
  List<Map<String, dynamic>> _accounts = const [];

  @override
  void initState() {
    super.initState();
    _savings = SavingsService(workspaceId: widget.workspaceId);
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
      _loading = _accounts.isEmpty;
      _error = null;
    });
    try {
      final accounts =
          await _savings.fetchSavingsAccountsRaw(source: Source.server);
      if (!mounted) return;
      setState(() {
        _accounts = accounts;
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

  double _accTotal(Map<String, dynamic> a) =>
      (a['total_amount'] is num) ? (a['total_amount'] as num).toDouble() : 0.0;

  List<Map<String, dynamic>> _savingsOf(Map<String, dynamic> a) {
    final raw = a['savings'];
    final out = <Map<String, dynamic>>[];
    if (raw is List) {
      for (final it in raw) {
        if (it is Map) out.add(it.map((k, v) => MapEntry('$k', v)));
      }
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final total = _accounts.fold<double>(0, (s, a) => s + _accTotal(a));
    return Scaffold(
      backgroundColor: AppColors.screen,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            TabTopBar(
              title: 'חסכונות',
              workspaceId: widget.workspaceId,
              syncing: _syncing,
              onSync: () => _pull(showToast: true),
              extraIcon: Icons.edit_rounded,
              onExtra: () async {
                await Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) =>
                        SavingsScreen(workspaceId: widget.workspaceId)));
                if (mounted) _pull(showToast: false);
              },
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(child: Text('שגיאה: $_error'))
                      : ListView(
                          padding: const EdgeInsets.fromLTRB(16, 4, 16, 110),
                          children: [
                            _hero(total),
                            const SizedBox(height: 16),
                            if (_accounts.isEmpty)
                              const Padding(
                                padding: EdgeInsets.symmetric(vertical: 24),
                                child: Center(
                                    child: Text('אין חשבונות חיסכון עדיין')),
                              )
                            else
                              for (final a in _accounts) ...[
                                _accountCard(a),
                                const SizedBox(height: 12),
                              ],
                          ],
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _hero(double total) {
    return HeroCard(
      background: AppColors.sage,
      padding: const EdgeInsets.all(20),
      children: [
        Row(
          children: [
            Container(
              width: 22,
              height: 22,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text('🐷', style: TextStyle(fontSize: 12)),
            ),
            const SizedBox(width: 8),
            const Text('סה״כ חסכונות',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF54613F))),
          ],
        ),
        const SizedBox(height: 8),
        Text(fmtMoney(total, decimals: false),
            style: const TextStyle(
                fontSize: 34,
                fontWeight: FontWeight.w800,
                letterSpacing: -1,
                color: Color(0xFF26301C))),
      ],
    );
  }

  Widget _accountCard(Map<String, dynamic> a) {
    final name = (a['name'] as String?)?.trim() ?? '';
    final total = _accTotal(a);
    final savings = _savingsOf(a);
    final sum = savings.fold<double>(
        0,
        (s, m) =>
            s + ((m['amount'] is num) ? (m['amount'] as num).toDouble() : 0.0));
    return AppCard(
      radius: 22,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                    color: AppColors.sageSoft,
                    borderRadius: BorderRadius.circular(13)),
                child: const Icon(Icons.savings_rounded,
                    size: 20, color: Color(0xFF4D5945)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(name.isEmpty ? 'חיסכון' : name,
                    style: const TextStyle(
                        fontSize: 15, fontWeight: FontWeight.w800)),
              ),
              Text(fmtMoney(total, decimals: false),
                  style: const TextStyle(
                      fontSize: 15.5,
                      fontWeight: FontWeight.w800,
                      color: AppColors.green)),
            ],
          ),
          if (savings.isNotEmpty) ...[
            const SizedBox(height: 13),
            _allocationBar(savings, sum),
            const SizedBox(height: 4),
            for (var i = 0; i < savings.length; i++) _savingRow(savings[i], i),
          ],
        ],
      ),
    );
  }

  Widget _allocationBar(List<Map<String, dynamic>> savings, double sum) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(99),
      child: SizedBox(
        height: 7,
        child: Row(
          children: [
            for (var i = 0; i < savings.length; i++)
              Expanded(
                flex: _amt(savings[i]) <= 0
                    ? 1
                    : (sum <= 0 ? 1 : (_amt(savings[i]) / sum * 1000).round()),
                child: Container(
                  margin: EdgeInsetsDirectional.only(
                      end: i == savings.length - 1 ? 0 : 2),
                  color:
                      AppColors.categorical[i % AppColors.categorical.length],
                ),
              ),
          ],
        ),
      ),
    );
  }

  double _amt(Map<String, dynamic> m) =>
      (m['amount'] is num) ? (m['amount'] as num).toDouble() : 0.0;

  Widget _savingRow(Map<String, dynamic> m, int i) {
    final name = (m['name'] as String?)?.trim() ?? '';
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: AppColors.line)),
      ),
      child: Row(
        children: [
          Container(
            width: 9,
            height: 9,
            decoration: BoxDecoration(
              color: AppColors.categorical[i % AppColors.categorical.length],
              borderRadius: BorderRadius.circular(3),
            ),
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(name.isEmpty ? 'חיסכון' : name,
                style: const TextStyle(
                    fontSize: 13.5, fontWeight: FontWeight.w600)),
          ),
          Text(fmtMoney(_amt(m), decimals: false),
              style:
                  const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }
}
