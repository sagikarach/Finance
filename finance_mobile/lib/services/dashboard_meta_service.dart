import 'package:cloud_firestore/cloud_firestore.dart';

class DashboardMeta {
  final double totalAll;
  final double totalLiquid;
  final double avgMonthlyIncome;
  final double avgMonthlyExpense;
  final int avgMonthsCount;
  final String computedAt;

  DashboardMeta({
    required this.totalAll,
    required this.totalLiquid,
    required this.avgMonthlyIncome,
    required this.avgMonthlyExpense,
    required this.avgMonthsCount,
    required this.computedAt,
  });

  static DashboardMeta fromFirestore(Map<String, dynamic> data) {
    double numField(String k) => (data[k] is num) ? (data[k] as num).toDouble() : 0.0;
    int intField(String k) => (data[k] is num) ? (data[k] as num).toInt() : 0;
    String strField(String k) => (data[k] as String?) ?? '';

    return DashboardMeta(
      totalAll: numField('total_all'),
      totalLiquid: numField('total_liquid'),
      avgMonthlyIncome: numField('avg_monthly_income'),
      avgMonthlyExpense: numField('avg_monthly_expense'),
      avgMonthsCount: intField('avg_months_count'),
      computedAt: strField('computed_at'),
    );
  }
}

class DashboardMetaService {
  final String workspaceId;

  DashboardMetaService({required this.workspaceId});

  Future<DashboardMeta?> fetch({
    Source source = Source.server,
  }) async {
    final snap = await FirebaseFirestore.instance
        .collection('workspaces')
        .doc(workspaceId)
        .collection('meta')
        .doc('dashboard')
        .get(GetOptions(source: source));
    final data = snap.data();
    if (data == null) return null;
    return DashboardMeta.fromFirestore(data);
  }
}


