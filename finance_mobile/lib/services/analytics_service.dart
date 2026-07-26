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
  final List<MonthBucket> months; // last 6, oldest -> newest
  final List<CategorySlice> expenseByCategory; // current month, desc
  final double monthIncome;
  final double monthExpense;
  final List<Movement> recent; // newest first

  const AnalyticsSummary({
    required this.months,
    required this.expenseByCategory,
    required this.monthIncome,
    required this.monthExpense,
    required this.recent,
  });

  static const empty = AnalyticsSummary(
    months: [],
    expenseByCategory: [],
    monthIncome: 0,
    monthExpense: 0,
    recent: [],
  );
}

class AnalyticsService {
  final String workspaceId;
  final MovementsService _movements;

  AnalyticsService({required this.workspaceId})
      : _movements = MovementsService(workspaceId: workspaceId);

  /// One-time (חד פעמי / ONE_TIME) and monthly-recurring (חודשי / MONTHLY)
  /// movements are excluded from the home cash-flow and breakdown charts.
  static bool _excludedFromFlow(String type) {
    final t = type.trim();
    return t == 'ONE_TIME' ||
        t == 'MONTHLY' ||
        t == 'חד פעמי' ||
        t == 'חד־פעמי' ||
        t == 'חודשי';
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

    final curKey = '${now.year}-${now.month.toString().padLeft(2, '0')}';
    final catMap = <String, double>{};
    double monthIncome = 0, monthExpense = 0;

    for (final m in all) {
      // The cash-flow / breakdown charts show only irregular real spending —
      // recurring monthly and one-time template movements are excluded.
      if (_excludedFromFlow(m.type)) continue;
      final dt = _parse(m.date);
      if (dt == null) continue;
      final key = '${dt.year}-${dt.month.toString().padLeft(2, '0')}';
      final b = buckets[key];
      if (b != null) {
        if (m.amount >= 0) {
          b.income += m.amount;
        } else {
          b.expense += m.amount.abs();
        }
      }
      if (key == curKey) {
        if (m.amount >= 0) {
          monthIncome += m.amount;
        } else {
          monthExpense += m.amount.abs();
          final cat = m.category.trim().isEmpty ? 'אחר' : m.category.trim();
          catMap[cat] = (catMap[cat] ?? 0) + m.amount.abs();
        }
      }
    }

    final months = order.map((k) => buckets[k]!).toList();

    final cats = catMap.entries
        .map((e) => CategorySlice(e.key, e.value))
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
      expenseByCategory: slices,
      monthIncome: monthIncome,
      monthExpense: monthExpense,
      recent: recent,
    );
  }
}
