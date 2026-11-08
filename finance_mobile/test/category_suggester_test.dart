import 'package:flutter_test/flutter_test.dart';
import 'package:finance_mobile/models/movement.dart';
import 'package:finance_mobile/models/movement_type.dart';
import 'package:finance_mobile/services/category_suggester.dart';

int _seq = 0;
Movement mv(double amount, String desc, String cat,
        {String type = MovementType.oneTime, bool transfer = false}) =>
    Movement(
      id: 'm${_seq++}',
      amount: amount,
      date: '2026-05-01',
      accountName: 'בנק',
      category: cat,
      type: type,
      description: desc,
      isTransfer: transfer,
    );

const allowed = ['ועד בית', 'סופר ומכולת', 'תרופות', 'טרם סווג', 'משכורת', 'קצבה'];

void main() {
  test('suggests the category (and type) of past expenses with that description', () {
    final s = CategorySuggester.fromMovements([
      for (var i = 0; i < 3; i++) mv(-45, 'סופרפארם לוד', 'תרופות'),
      for (var i = 0; i < 3; i++) mv(-440, 'ועד בית', 'ועד בית', type: MovementType.monthly),
    ], isIncome: false, allowedCategories: allowed);
    expect(s.suggest('סופרפארם לוד', 50)?.category, 'תרופות');
    final v = s.suggest('ועד בית', 440)!;
    expect(v.category, 'ועד בית');
    expect(v.type, MovementType.monthly);
  });

  test('the same description beats a partial match with a closer amount', () {
    // Mirrors the desktop fix: "ועד בית" for ₪48 must not become the bakery
    // "בית הפיתה" just because bakery purchases cost about ₪50.
    CategorySuggester build(int exact) => CategorySuggester.fromMovements([
          for (var i = 0; i < 5; i++) mv(-50, 'בית הפיתה ליז', 'סופר ומכולת'),
          for (var i = 0; i < exact; i++) mv(-440, 'ועד בית', 'ועד בית'),
        ], isIncome: false, allowedCategories: allowed);
    final five = build(5).suggest('ועד בית', 48)!;
    expect(five.category, 'ועד בית');
    // Same score as the desktop classifier on identical data (parity check).
    expect(five.confidence, closeTo(0.528, 1e-9));
    // With only 4 examples the desktop scores 0.4752 (< 0.5): no suggestion —
    // and never the bakery's category.
    expect(build(4).suggest('ועד בית', 48), isNull);
  });

  test('no suggestion for unknown, unclassified or empty descriptions', () {
    final s = CategorySuggester.fromMovements([
      for (var i = 0; i < 3; i++) mv(-100, 'BIT', 'טרם סווג'),
      for (var i = 0; i < 3; i++) mv(-45, 'סופרפארם לוד', 'תרופות'),
    ], isIncome: false, allowedCategories: allowed);
    expect(s.suggest('חנות שלא ראינו מעולם', 50), isNull);
    expect(s.suggest('BIT', 100), isNull);
    expect(s.suggest('', 10), isNull);
  });

  test('income learns only from income; transfers never teach', () {
    final history = [
      for (var i = 0; i < 3; i++) mv(12876, 'משכורת שגיא', 'משכורת', type: MovementType.monthly),
      for (var i = 0; i < 3; i++) mv(-60, 'משכורת שגיא', 'תרופות'), // expenses
      for (var i = 0; i < 3; i++) mv(500, 'קצבת ילדים', 'קצבה', transfer: true),
    ];
    final income = CategorySuggester.fromMovements(history,
        isIncome: true, allowedCategories: allowed);
    expect(income.suggest('משכורת שגיא', 12876)?.category, 'משכורת');
    expect(income.suggest('קצבת ילדים', 500), isNull);
    final expense = CategorySuggester.fromMovements(history,
        isIncome: false, allowedCategories: allowed);
    expect(expense.suggest('משכורת שגיא', 60)?.category, 'תרופות');
  });

  test('an exact description takes the type it had most often', () {
    // Monthly 4 times (other amounts), one-time once at exactly this amount.
    final s = CategorySuggester.fromMovements([
      for (var i = 0; i < 4; i++)
        mv(-400, 'SHEIN.COM', 'סופר ומכולת', type: MovementType.monthly),
      mv(-120, 'SHEIN.COM', 'סופר ומכולת'),
    ], isIncome: false, allowedCategories: allowed);
    expect(s.suggest('SHEIN.COM', 120)?.type, MovementType.monthly);
  });
}
