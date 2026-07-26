import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../services/assets_service.dart';
import '../services/session_service.dart';
import '../widgets/header_actions_row.dart';
import '../widgets/notifications_sheet.dart';

class AssetsScreen extends StatefulWidget {
  final String workspaceId;

  const AssetsScreen({super.key, required this.workspaceId});

  @override
  State<AssetsScreen> createState() => _AssetsScreenState();
}

class _AssetsScreenState extends State<AssetsScreen> {
  bool _syncing = false;
  bool _loading = true;
  String? _error;

  final SessionService _session = const SessionService();
  late final AssetsService _assets;

  List<Asset> _items = <Asset>[];

  @override
  void initState() {
    super.initState();
    _assets = AssetsService(workspaceId: widget.workspaceId);
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
      final items = await _assets.fetch(source: Source.server);
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

  // ── formatting helpers ────────────────────────────────────────────────

  String _fmtMoney(double v) {
    final neg = v < 0;
    final fixed = v.abs().toStringAsFixed(2);
    final dot = fixed.indexOf('.');
    final intPart = fixed.substring(0, dot);
    final frac = fixed.substring(dot);
    final buf = StringBuffer();
    for (var i = 0; i < intPart.length; i++) {
      if (i > 0 && (intPart.length - i) % 3 == 0) buf.write(',');
      buf.write(intPart[i]);
    }
    return '${neg ? '-' : ''}$buf$frac ₪';
  }

  String _fmtPct(double v) {
    var s = v.toStringAsFixed(2);
    if (s.endsWith('0')) s = s.substring(0, s.length - 1);
    if (s.endsWith('0')) s = s.substring(0, s.length - 2);
    return '$s%';
  }

  String _fmtTerm(int months) {
    if (months <= 0) return '';
    if (months % 12 == 0) return '${months ~/ 12} שנים';
    return '$months חודשים';
  }

  String _trackRateLabel(MortgageTrack t) {
    if (t.isPrime) {
      final sign = t.primeSpread >= 0 ? '+' : '-';
      final spread = _fmtPct(t.primeSpread.abs());
      return 'פריים $sign $spread · ≈${_fmtPct(t.effectiveAnnualRate)}';
    }
    return _fmtPct(t.annualRate);
  }

  // ── build ─────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    if (!_session.isLoggedIn) {
      return const Scaffold(body: Center(child: Text('לא מחובר')));
    }

    return Scaffold(
      appBar: AppBar(
        title: HeaderActionsRow(
          title: 'נכסים',
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
              icon: Icons.sync,
              tooltip: 'סנכרן עכשיו',
              onPressed: _syncing ? null : () => _pullFromServer(showToast: true),
            ),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : (_error != null)
              ? Center(child: Text('שגיאה: $_error'))
              : _items.isEmpty
                  ? const Center(
                      child: Text('אין נכסים עדיין. הוסף נכס בדסקטופ וסנכרן.'),
                    )
                  : ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        _summaryCard(),
                        const SizedBox(height: 16),
                        ..._items.map(_assetCard),
                      ],
                    ),
    );
  }

  Widget _summaryCard() {
    final totalValue = _items.fold(0.0, (s, a) => s + a.value);
    final totalDebt = _items.fold(0.0, (s, a) => s + a.mortgagePrincipal);
    final net = totalValue - totalDebt;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _summaryRow('שווי נכסים', totalValue, Colors.green.shade700),
            if (totalDebt > 0) ...[
              const SizedBox(height: 8),
              _summaryRow('יתרת משכנתא', totalDebt, Colors.red.shade700),
              const Divider(height: 20),
              _summaryRow('שווי נטו', net,
                  net >= 0 ? Colors.green.shade700 : Colors.red.shade700,
                  bold: true),
            ],
          ],
        ),
      ),
    );
  }

  Widget _summaryRow(String label, double value, Color color,
      {bool bold = false}) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: TextStyle(
              fontWeight: bold ? FontWeight.w900 : FontWeight.w700,
              fontSize: bold ? 17 : 15,
            ),
          ),
        ),
        Text(
          _fmtMoney(value),
          style: TextStyle(
            color: color,
            fontWeight: FontWeight.w900,
            fontSize: bold ? 18 : 16,
          ),
        ),
      ],
    );
  }

  Widget _assetCard(Asset a) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // ── header: name + kind chip + value ──
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          a.name.isEmpty ? 'נכס' : a.name,
                          style: Theme.of(context)
                              .textTheme
                              .titleLarge
                              ?.copyWith(
                                fontWeight: FontWeight.w900,
                                fontSize: 20,
                              ),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            _chip(a.isHouse ? 'בית' : 'נכס',
                                Colors.blue.shade700),
                            if (a.sold) ...[
                              const SizedBox(width: 6),
                              _chip('נמכר', Colors.grey.shade600),
                            ],
                          ],
                        ),
                      ],
                    ),
                  ),
                  Text(
                    _fmtMoney(a.value),
                    style: TextStyle(
                      color: Colors.green.shade700,
                      fontWeight: FontWeight.w900,
                      fontSize: 20,
                    ),
                  ),
                ],
              ),

              // ── mortgage section (houses with tracks) ──
              if (a.isHouse && a.hasMortgage) ...[
                const Divider(height: 24),
                _kv('יתרת משכנתא', _fmtMoney(a.mortgagePrincipal),
                    valueColor: Colors.red.shade700),
                const SizedBox(height: 6),
                _kv('תשלום חודשי (הערכה)', _fmtMoney(a.monthlyPayment)),
                const SizedBox(height: 6),
                _kv('הון עצמי (הערכה)', _fmtMoney(a.equity),
                    valueColor: a.equity >= 0
                        ? Colors.green.shade700
                        : Colors.red.shade700),
                const SizedBox(height: 12),
                Text(
                  'מסלולי משכנתא (${a.tracks.length})',
                  style: const TextStyle(
                      fontWeight: FontWeight.w800, fontSize: 14),
                ),
                const SizedBox(height: 4),
                ...a.tracks.map(_trackTile),
              ] else if (a.isHouse && !a.hasMortgage) ...[
                const Divider(height: 24),
                const Text('אין מסלולי משכנתא',
                    style: TextStyle(color: Colors.grey)),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _trackTile(MortgageTrack t) {
    final meta = <String>[
      _trackRateLabel(t),
      if (t.termMonths > 0) _fmtTerm(t.termMonths),
      if (t.amortization.isNotEmpty) t.amortization,
      if (t.cpiLinked) 'צמוד מדד',
    ].where((s) => s.isNotEmpty).join(' · ');

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? Colors.white.withValues(alpha: 0.04)
            : Colors.black.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  t.name.isEmpty ? (t.kind.isEmpty ? 'מסלול' : t.kind) : t.name,
                  style: const TextStyle(
                      fontWeight: FontWeight.w800, fontSize: 15),
                ),
              ),
              Text(
                _fmtMoney(t.principal),
                style: const TextStyle(
                    fontWeight: FontWeight.w800, fontSize: 15),
              ),
            ],
          ),
          if (t.kind.isNotEmpty && t.name.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(t.kind,
                  style: TextStyle(
                      color: Colors.grey.shade600, fontSize: 12)),
            ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: Text(
                  meta,
                  style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                ),
              ),
              if (t.monthlyPayment > 0)
                Text(
                  '${_fmtMoney(t.monthlyPayment)} לחודש',
                  style: TextStyle(
                      color: Colors.grey.shade800,
                      fontSize: 13,
                      fontWeight: FontWeight.w600),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _kv(String label, String value, {Color? valueColor}) {
    return Row(
      children: [
        Expanded(
          child: Text(label,
              style:
                  const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        ),
        Text(
          value,
          style: TextStyle(
            color: valueColor,
            fontWeight: FontWeight.w800,
            fontSize: 15,
          ),
        ),
      ],
    );
  }

  Widget _chip(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        text,
        style: TextStyle(
            color: color, fontSize: 12, fontWeight: FontWeight.w700),
      ),
    );
  }
}
