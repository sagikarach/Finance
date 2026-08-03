import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../../services/assets_service.dart';
import '../../services/session_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/money.dart';
import '../../widgets/charts/donut_chart.dart';
import '../../widgets/ui/cards.dart';
import '../../widgets/ui/tab_top_bar.dart';

class AssetsTab extends StatefulWidget {
  final String workspaceId;
  final Listenable refresh;
  const AssetsTab(
      {super.key, required this.workspaceId, required this.refresh});

  @override
  State<AssetsTab> createState() => _AssetsTabState();
}

class _AssetsTabState extends State<AssetsTab> {
  final SessionService _session = const SessionService();
  late final AssetsService _assets;

  bool _loading = true;
  bool _syncing = false;
  String? _error;
  List<Asset> _items = const [];

  @override
  void initState() {
    super.initState();
    _assets = AssetsService(workspaceId: widget.workspaceId);
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
      final items = await _assets.fetch(source: Source.server);
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.screen,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            TabTopBar(
              title: 'נכסים',
              workspaceId: widget.workspaceId,
              syncing: _syncing,
              onSync: () => _pull(showToast: true),
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(child: Text('שגיאה: $_error'))
                      : _items.isEmpty
                          ? const Center(
                              child: Text('אין נכסים עדיין. הוסף נכס בדסקטופ.'))
                          : ListView(
                              padding:
                                  const EdgeInsets.fromLTRB(16, 4, 16, 110),
                              children: [
                                for (final a in _items) ..._assetBlock(a),
                              ],
                            ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _assetBlock(Asset a) {
    final widgets = <Widget>[
      _hero(a),
      const SizedBox(height: 16),
    ];
    if (a.isHouse && a.hasMortgage) {
      widgets.addAll([
        _mortgageDonut(a),
        const SizedBox(height: 14),
        _statRow(a),
        const SizedBox(height: 16),
        SectionHeader(
            title: 'מסלולי משכנתא', actionLabel: '${a.tracks.length}'),
        const SizedBox(height: 12),
        for (final t in a.tracks) ...[
          _trackTile(t),
          const SizedBox(height: 12),
        ],
      ]);
    }
    widgets.add(const SizedBox(height: 22));
    return widgets;
  }

  Widget _hero(Asset a) {
    final Color bg;
    final String badge;
    final String fallbackName;
    if (a.isCar) {
      bg = AppColors.yellowSoft;
      badge = '🚗 רכב';
      fallbackName = 'רכב';
    } else if (a.isHouse) {
      bg = AppColors.lav;
      badge = '🏠 נדל״ן';
      fallbackName = 'נדל״ן';
    } else {
      bg = AppColors.sage;
      badge = '💼 נכס';
      fallbackName = 'נכס';
    }
    return HeroCard(
      background: bg,
      center: true,
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
      children: [
        TagChip(
          text: badge,
          color: const Color(0xFF39366A),
        ),
        const SizedBox(height: 10),
        Text(a.name.isEmpty ? fallbackName : a.name,
            textAlign: TextAlign.center,
            style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: Color(0xFF26243F))),
        const SizedBox(height: 11),
        const Text('שווי הנכס',
            style: TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w700,
                color: Color(0xFF57548C))),
        const SizedBox(height: 2),
        Text(fmtMoney(a.value, decimals: false),
            style: const TextStyle(
                fontSize: 31,
                fontWeight: FontWeight.w800,
                letterSpacing: -1,
                color: Color(0xFF211F38))),
        if (a.isHouse && a.hasMortgage) ...[
          const SizedBox(height: 6),
          Text(
            'הון עצמי ${fmtMoney(a.equity, decimals: false)}',
            style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: Color(0xFF1F7A4E)),
          ),
        ],
      ],
    );
  }

  Widget _mortgageDonut(Asset a) {
    final equity = a.equity < 0 ? 0.0 : a.equity;
    return AppCard(
      child: Column(
        children: [
          DonutChart(
            size: 180,
            thickness: 24,
            segments: [
              DonutSegment(equity, AppColors.green),
              DonutSegment(a.mortgagePrincipal, AppColors.clay),
            ],
            center: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('משכנתא',
                    style: TextStyle(
                        color: AppColors.muted,
                        fontSize: 11,
                        fontWeight: FontWeight.w600)),
                Text(fmtCompact(a.mortgagePrincipal),
                    style: const TextStyle(
                        fontSize: 22, fontWeight: FontWeight.w800)),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _legendDot(AppColors.green, 'הון עצמי'),
              const SizedBox(width: 22),
              _legendDot(AppColors.clay, 'יתרת חוב'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _legendDot(Color c, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
            width: 11,
            height: 11,
            decoration: BoxDecoration(
                color: c, borderRadius: BorderRadius.circular(4))),
        const SizedBox(width: 8),
        Text(label,
            style:
                const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
      ],
    );
  }

  Widget _statRow(Asset a) {
    return Row(
      children: [
        Expanded(
            child: _stat('יתרת משכנתא', fmtCompact(a.mortgagePrincipal),
                AppColors.clay)),
        const SizedBox(width: 12),
        Expanded(
            child: _stat('תשלום חודשי',
                fmtMoney(a.monthlyPayment, decimals: false), null)),
      ],
    );
  }

  Widget _stat(String label, String value, Color? color) {
    return AppCard(
      radius: 20,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
      child: Column(
        children: [
          Text(label,
              style: const TextStyle(
                  color: AppColors.muted,
                  fontSize: 11,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(value,
              style: TextStyle(
                  fontSize: 15.5, fontWeight: FontWeight.w800, color: color)),
        ],
      ),
    );
  }

  Widget _trackTile(MortgageTrack t) {
    final meta = <String>[
      _rateLabel(t),
      if (t.termMonths > 0) _termLabel(t.termMonths),
      if (t.amortization.isNotEmpty) t.amortization,
      if (t.cpiLinked) 'צמוד מדד',
    ].where((s) => s.isNotEmpty).join(' · ');

    return AppCard(
      radius: 18,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  t.name.isEmpty ? (t.kind.isEmpty ? 'מסלול' : t.kind) : t.name,
                  style: const TextStyle(
                      fontWeight: FontWeight.w800, fontSize: 14.5),
                ),
              ),
              Text(fmtMoney(t.principal, decimals: false),
                  style: const TextStyle(
                      fontWeight: FontWeight.w800, fontSize: 14.5)),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: Text(meta,
                    style: const TextStyle(
                        color: AppColors.muted, fontSize: 12.5)),
              ),
              if (t.monthlyPayment > 0)
                Text('${fmtMoney(t.monthlyPayment, decimals: false)}/ח׳',
                    style: const TextStyle(
                        color: Color(0xFF5C5F57),
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700)),
            ],
          ),
        ],
      ),
    );
  }

  String _pct(double v) {
    var s = v.toStringAsFixed(2);
    if (s.endsWith('0')) s = s.substring(0, s.length - 1);
    if (s.endsWith('0')) s = s.substring(0, s.length - 2);
    if (s.endsWith('.')) s = s.substring(0, s.length - 1);
    return '$s%';
  }

  String _rateLabel(MortgageTrack t) {
    if (t.isPrime) {
      final sign = t.primeSpread >= 0 ? '+' : '−';
      return 'פריים $sign ${_pct(t.primeSpread.abs())} · ≈${_pct(t.effectiveAnnualRate)}';
    }
    return _pct(t.annualRate);
  }

  String _termLabel(int months) =>
      months % 12 == 0 ? '${months ~/ 12} שנים' : '$months חודשים';
}
