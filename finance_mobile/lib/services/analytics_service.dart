import 'package:cloud_firestore/cloud_firestore.dart';

import '../models/movement.dart';
import 'movements_service.dart';

const List<String> hebMonthsShort = [
  'ינו',
  'פבר',
  'מרץ',
  'אפר',
  'מאי',
  'יוני',
  'יול',
  'אוג',
  'ספט',
  'אוק',
  'נוב',
  'דצמ',
];

class MonthBucket {
  final int year;
  final int month;
  double income = 0;
  double expense = 0;
  MonthBucket(this.year, this.month);
  double get net => income - expense;
  String get label => hebMonthsShort[month - 1];
}

class CategorySlice {
  final String name;
  final double amount;
  const CategorySlice(this.name, this.amount);
}

class AnalyticsSummary {
  final List<MonthBucket> months; // last 6, oldest -> newest (monthly-type net)
  final List<CategorySlice> avgByCategory; // avg monthly expense per category
  final double avgMonthlyIncome;
  final double avgMonthlyExpense;
  final List<Movement> recent; // newest first (all movements)

  const AnalyticsSummary({
    required this.months,
    required this.avgByCategory,
    required this.avgMonthlyIncome,
    required this.avgMonthlyExpense,
    required this.recent,
  });

  double get avgMonthlyNet => avgMonthlyIncome - avgMonthlyExpense;

  static const empty = AnalyticsSummary(
    months: [],
    avgByCategory: [],
    avgMonthlyIncome: 0,
    avgMonthlyExpense: 0,
    recent: [],
  );
}

class AnalyticsService {
  final String workspaceId;
  final MovementsService _movements;

  AnalyticsService({required this.workspaceId})
      : _movements = MovementsService(workspaceId: workspaceId);

  /// The home charts show only the regular *monthly* recurring flow —
  /// one-time (חד פעמי) and yearly (שנתי) movements are excluded.
  static bool _isMonthly(String type) {
    final t = type.trim();
    return t == 'MONTHLY' || t == 'חודשי';
  }

  DateTime? _parse(String s) {
    final t = s.trim();
    if (t.length < 7) return null;
    try {
      return DateTime.parse(t.length == 7 ? '$t-01' : t);
    } catch (_) {
      return null;
    }
  }

  Future<AnalyticsSummary> compute({Source source = Source.server}) async {
    final all = await _movements.fetch(source: source);
    final now = DateTime.now();

    // Last 6 months (oldest -> newest).
    final buckets = <String, MonthBucket>{};
    final order = <String>[];
    for (var i = 5; i >= 0; i--) {
      final total = now.year * 12 + (now.month - 1) - i;
      final yy = total ~/ 12;
      final mm = total % 12 + 1;
      final key = '$yy-${mm.toString().padLeft(2, '0')}';
      buckets[key] = MonthBucket(yy, mm);
      order.add(key);
    }

    // Sum monthly-type movements over the window; the donut/chip then show the
    // per-month AVERAGE (not the noisy current month).
    final catSum = <String, double>{};
    double incomeWindow = 0, expenseWindow = 0;

    for (final m in all) {
      if (!_isMonthly(m.type)) continue; // exclude one-time & yearly
      final dt = _parse(m.date);
      if (dt == null) continue;
      final key = '${dt.year}-${dt.month.toString().padLeft(2, '0')}';
      final b = buckets[key];
      if (b == null) continue; // only within the 6-month window
      if (m.amount >= 0) {
        b.income += m.amount;
        incomeWindow += m.amount;
      } else {
        final a = m.amount.abs();
        b.expense += a;
        expenseWindow += a;
        final cat = m.category.trim().isEmpty ? 'אחר' : m.category.trim();
        catSum[cat] = (catSum[cat] ?? 0) + a;
      }
    }

    final months = order.map((k) => buckets[k]!).toList();

    // Average over the months that actually have activity (avoids understating
    // for new workspaces with < 6 months of history).
    final monthsWithData =
        months.where((b) => b.income > 0 || b.expense > 0).length;
    final div = monthsWithData < 1 ? 1 : monthsWithData;

    final cats = catSum.entries
        .map((e) => CategorySlice(e.key, e.value / div))
        .toList()
      ..sort((a, b) => b.amount.compareTo(a.amount));
    // Collapse a long tail into "אחר".
    List<CategorySlice> slices;
    if (cats.length > 5) {
      final top = cats.take(4).toList();
      final rest = cats.skip(4).fold<double>(0, (s, c) => s + c.amount);
      slices = [...top, CategorySlice('אחר', rest)];
    } else {
      slices = cats;
    }

    final recent = [...all]..sort((a, b) {
        final c = b.date.compareTo(a.date);
        if (c != 0) return c;
        return (b.updatedAtMs ?? 0).compareTo(a.updatedAtMs ?? 0);
      });

    return AnalyticsSummary(
      months: months,
      avgByCategory: slices,
      avgMonthlyIncome: incomeWindow / div,
      avgMonthlyExpense: expenseWindow / div,
      recent: recent,
    );
  }
}
