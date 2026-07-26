import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../../services/analytics_service.dart';
import '../../services/bootstrap_service.dart';
import '../../services/dashboard_meta_service.dart';
import '../../services/session_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/money.dart';
import '../../widgets/charts/bars_chart.dart';
import '../../widgets/charts/donut_chart.dart';
import '../../widgets/charts/sparkline.dart';
import '../../widgets/notifications_sheet.dart';
import '../../widgets/ui/cards.dart';
import '../../widgets/ui/tx_tile.dart';

class HomeTab extends StatefulWidget {
  final String workspaceId;
  final Listenable refresh;
  final VoidCallback onAdd;
  final VoidCallback? onSeeTransactions;

  const HomeTab({
    super.key,
    required this.workspaceId,
    required this.refresh,
    required this.onAdd,
    this.onSeeTransactions,
  });

  @override
  State<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<HomeTab> {
  final SessionService _session = const SessionService();
  late final BootstrapService _bootstrap;
  late final DashboardMetaService _meta;
  late final AnalyticsService _analytics;

  bool _loading = true;
  bool _syncing = false;
  String? _error;
  DashboardMeta? _dash;
  AnalyticsSummary _sum = AnalyticsSummary.empty;

  @override
  void initState() {
    super.initState();
    _bootstrap = BootstrapService(workspaceId: widget.workspaceId);
    _meta = DashboardMetaService(workspaceId: widget.workspaceId);
    _analytics = AnalyticsService(workspaceId: widget.workspaceId);
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
      _loading = _dash == null;
      _error = null;
    });
    try {
      await _bootstrap.ensureWorkspaceMeta();
      final dash = await _meta.fetch(source: Source.server);
      final sum = await _analytics.compute(source: Source.server);
      if (!mounted) return;
      setState(() {
        _dash = dash;
        _sum = sum;
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

  String get _firstName {
    final n = FirebaseAuth.instance.currentUser?.displayName?.trim() ?? '';
    if (n.isEmpty) return '';
    return n.split(' ').first;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.screen,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _header(),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(child: Text('שגיאה: $_error'))
                      : ListView(
                          padding: const EdgeInsets.fromLTRB(16, 4, 16, 110),
                          children: _content(),
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _header() {
    final name = _firstName;
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 6, 18, 8),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('שלום 👋',
                    style: TextStyle(color: AppColors.muted, fontSize: 13)),
                const SizedBox(height: 1),
                Text(name.isEmpty ? 'ברוך הבא' : name,
                    style: const TextStyle(
                        fontSize: 17, fontWeight: FontWeight.w800)),
              ],
            ),
          ),
          _roundIcon(
              Icons.notifications_none_rounded,
              () => showNotificationsSheet(
                  context: context, workspaceId: widget.workspaceId)),
          const SizedBox(width: 8),
          _roundIcon(
              _syncing ? Icons.hourglass_top_rounded : Icons.sync_rounded,
              _syncing ? null : () => _pull(showToast: true)),
        ],
      ),
    );
  }

  Widget _roundIcon(IconData icon, VoidCallback? onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: const Color(0xFFEFEDE4),
          borderRadius: BorderRadius.circular(13),
        ),
        child: Icon(icon, size: 20, color: AppColors.muted),
      ),
    );
  }

  List<Widget> _content() {
    final totalAll = _dash?.totalAll ?? 0;
    final liquid = _dash?.totalLiquid ?? 0;
    final monthNet = _sum.monthIncome - _sum.monthExpense;
    final rawPct = _sum.monthIncome > 0
        ? (monthNet / _sum.monthIncome * 100).round()
        : null;
    // Only show the savings-rate badge when it's a sane figure (0–100%).
    final savingsPct =
        (rawPct != null && rawPct >= 0 && rawPct <= 100) ? rawPct : null;

    return [
      _balanceHero(totalAll, monthNet, savingsPct),
      const SizedBox(height: 14),
      _chipsRow(liquid, monthNet),
      const SizedBox(height: 16),
      if (_sum.months.isNotEmpty) ...[
        _cashflowCard(),
        const SizedBox(height: 16),
      ],
      if (_sum.expenseByCategory.isNotEmpty) ...[
        _expenseCard(),
        const SizedBox(height: 16),
      ],
      SectionHeader(
        title: 'תנועות אחרונות',
        actionLabel: 'הצג הכל',
        onAction: widget.onSeeTransactions,
      ),
      const SizedBox(height: 10),
      if (_sum.recent.isEmpty)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 20),
          child: Center(child: Text('אין תנועות עדיין')),
        )
      else
        ..._sum.recent.take(4).map((m) => TxTile(movement: m)),
    ];
  }

  Widget _balanceHero(double total, double monthNet, int? savingsPct) {
    final spark = _sum.months.map((b) => b.net).toList();
    return HeroCard(
      background: AppColors.yellow,
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
              child: const Text('₪',
                  style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF7A6420))),
            ),
            const SizedBox(width: 8),
            const Text('סה״כ כסף',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF7A6420))),
            const Spacer(),
            if (savingsPct != null)
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0x24241612),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text('$savingsPct% חיסכון',
                    style: const TextStyle(
                        color: Color(0xFF3F3616),
                        fontWeight: FontWeight.w700,
                        fontSize: 12)),
              ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          fmtMoney(total, decimals: false),
          style: const TextStyle(
            fontSize: 38,
            fontWeight: FontWeight.w800,
            letterSpacing: -1,
            color: Color(0xFF2C2612),
          ),
        ),
        if (spark.length >= 2) ...[
          const SizedBox(height: 6),
          Sparkline(values: spark, color: const Color(0xFF4F430F)),
        ],
      ],
    );
  }

  Widget _chipsRow(double liquid, double monthNet) {
    return Row(
      children: [
        Expanded(
          child: AppCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            radius: 22,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('נזיל',
                    style: TextStyle(
                        color: AppColors.muted,
                        fontSize: 12,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 5),
                Text(fmtMoney(liquid, decimals: false),
                    style: const TextStyle(
                        fontSize: 18, fontWeight: FontWeight.w800)),
              ],
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: AppCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            radius: 22,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('תזרים החודש',
                    style: TextStyle(
                        color: AppColors.muted,
                        fontSize: 12,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 5),
                Text(fmtSigned(monthNet, decimals: false),
                    textDirection: TextDirection.ltr,
                    style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        color:
                            monthNet >= 0 ? AppColors.green : AppColors.clay)),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _cashflowCard() {
    final months = _sum.months;
    var maxIdx = 0;
    for (var i = 0; i < months.length; i++) {
      if (months[i].net > months[maxIdx].net) maxIdx = i;
    }
    final bars = [
      for (var i = 0; i < months.length; i++)
        BarDatum(
          label: months[i].label,
          value: months[i].net.abs(),
          highlight: i == maxIdx,
          positive: months[i].net >= 0,
          tooltip: i == maxIdx ? fmtSigned(months[i].net, decimals: false) : null,
        ),
    ];
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SectionHeader(title: 'תזרים חודשי', actionLabel: '6 חודשים'),
          const SizedBox(height: 8),
          BarsChart(data: bars),
        ],
      ),
    );
  }

  Widget _expenseCard() {
    final slices = _sum.expenseByCategory;
    final total = slices.fold<double>(0, (s, c) => s + c.amount);
    final segs = [
      for (var i = 0; i < slices.length; i++)
        DonutSegment(slices[i].amount,
            AppColors.categorical[i % AppColors.categorical.length]),
    ];
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('פילוח הוצאות · החודש',
              style: TextStyle(
                  color: AppColors.muted,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 10),
          Center(
            child: DonutChart(
              size: 190,
              thickness: 24,
              segments: segs,
              center: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('סה״כ',
                      style: TextStyle(
                          color: AppColors.muted,
                          fontSize: 12,
                          fontWeight: FontWeight.w600)),
                  Text(fmtCompact(total),
                      style: const TextStyle(
                          fontSize: 26, fontWeight: FontWeight.w800)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          for (var i = 0; i < slices.length; i++)
            _legendRow(
              AppColors.categorical[i % AppColors.categorical.length],
              slices[i].name,
              total <= 0 ? 0 : (slices[i].amount / total * 100).round(),
              slices[i].amount,
            ),
        ],
      ),
    );
  }

  Widget _legendRow(Color c, String name, int pct, double amount) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Container(
            width: 11,
            height: 11,
            decoration:
                BoxDecoration(color: c, borderRadius: BorderRadius.circular(4)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                    fontSize: 13.5, fontWeight: FontWeight.w600)),
          ),
          Text('$pct%',
              style: const TextStyle(
                  color: AppColors.muted,
                  fontSize: 13,
                  fontWeight: FontWeight.w700)),
          const SizedBox(width: 14),
          Text(fmtMoney(amount, decimals: false),
              style:
                  const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }
}
