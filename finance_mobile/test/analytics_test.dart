import 'package:flutter_test/flutter_test.dart';
import 'package:finance_mobile/services/analytics_service.dart';
import 'package:finance_mobile/models/movement.dart';

Movement _mv(double amount, String date, {String type = 'MONTHLY', String category = ''}) {
  return Movement(
    id: '$date$amount$category',
    amount: amount,
    date: date,
    accountName: 'בנק',
    category: category,
    type: type,
  );
}

void main() {
  // June 2026 → window is Jan..Jun 2026 (6 months, oldest → newest).
  final now = DateTime(2026, 6, 15);

  final movements = <Movement>[
    _mv(1000, '2026-02-10', category: 'משכורת'),          // Feb income
    _mv(-300, '2026-02-12', category: 'מזון'),            // Feb expense
    _mv(-200, '2026-03-05', category: 'מזון'),            // Mar expense
    _mv(-100, '2026-04-05', category: 'תחבורה'),          // Apr expense
    _mv(500, '2026-06-01', category: 'משכורת'),           // Jun income
    _mv(-9999, '2026-05-01', type: 'ONE_TIME', category: 'x'), // excluded: not MONTHLY
    _mv(-50, '2025-12-20', category: 'מזון'),             // excluded: before window
  ];

  final s = AnalyticsService.summarize(movements, now);

  test('builds a 6-month window oldest→newest', () {
    expect(s.months.length, 6);
    expect(s.months.first.month, 1); // Jan 2026
    expect(s.months.last.month, 6); // Jun 2026
  });

  test('buckets monthly income/expense into the right month', () {
    final feb = s.months.firstWhere((b) => b.month == 2);
    expect(feb.income, 1000);
    expect(feb.expense, 300);
    expect(feb.net, 700);
    final jan = s.months.firstWhere((b) => b.month == 1);
    expect(jan.income, 0);
    expect(jan.expense, 0);
  });

  test('excludes one-time movements and out-of-window months', () {
    // the -9999 one-time and the 2025-12 movement must not inflate expenses
    final totalExpense = s.months.fold<double>(0, (a, b) => a + b.expense);
    expect(totalExpense, 600); // 300 + 200 + 100 only
  });

  test('averages over the months that actually have activity', () {
    // 4 months have data (Feb, Mar, Apr, Jun) → divide by 4, not 6
    expect(s.avgMonthlyIncome, 1500 / 4); // 375
    expect(s.avgMonthlyExpense, 600 / 4); // 150
    expect(s.avgMonthlyNet, 375 - 150);
  });

  test('category slices are per-month averages, largest first', () {
    expect(s.avgByCategory.length, 2);
    expect(s.avgByCategory.first.name, 'מזון');
    expect(s.avgByCategory.first.amount, 500 / 4); // (300+200)/4 = 125
    expect(s.avgByCategory[1].name, 'תחבורה');
    expect(s.avgByCategory[1].amount, 100 / 4); // 25
  });

  test('recent lists all movements, newest first', () {
    expect(s.recent.length, movements.length); // recent is unfiltered
    expect(s.recent.first.date, '2026-06-01');
  });

  test('empty input yields zeroed averages and 6 empty buckets', () {
    final e = AnalyticsService.summarize(<Movement>[], now);
    expect(e.months.length, 6);
    expect(e.avgMonthlyIncome, 0);
    expect(e.avgMonthlyExpense, 0);
    expect(e.avgByCategory, isEmpty);
  });
}
