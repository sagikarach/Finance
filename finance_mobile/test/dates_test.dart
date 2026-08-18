import 'package:flutter_test/flutter_test.dart';
import 'package:finance_mobile/utils/dates.dart';

void main() {
  group('parseFlexibleDate', () {
    test('ISO passes through', () {
      expect(parseFlexibleDate('2026-07-16'), DateTime(2026, 7, 16));
    });

    test('dd/mm/yyyy', () {
      expect(parseFlexibleDate('16/07/2026'), DateTime(2026, 7, 16));
    });

    test('dd-mm-yyyy (dashes)', () {
      expect(parseFlexibleDate('16-07-2026'), DateTime(2026, 7, 16));
    });

    test('dd.mm.yy (2-digit year)', () {
      expect(parseFlexibleDate('03.09.24'), DateTime(2024, 9, 3));
    });

    test('YYYY-MM month key -> first of month', () {
      expect(parseFlexibleDate('2026-07'), DateTime(2026, 7, 1));
    });

    test('garbage -> null', () {
      expect(parseFlexibleDate('not a date'), isNull);
      expect(parseFlexibleDate(''), isNull);
    });
  });

  group('toIsoDate', () {
    test('normalizes every supported shape to ISO', () {
      expect(toIsoDate('16/07/2026'), '2026-07-16');
      expect(toIsoDate('16-07-2026'), '2026-07-16');
      expect(toIsoDate('01/11/2025'), '2025-11-01');
      expect(toIsoDate('2026-07-16'), '2026-07-16');
    });

    test('returns the original unchanged when unparseable', () {
      expect(toIsoDate('whenever'), 'whenever');
    });
  });
}
