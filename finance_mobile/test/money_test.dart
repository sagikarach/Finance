import 'package:flutter_test/flutter_test.dart';
import 'package:finance_mobile/utils/money.dart';

void main() {
  group('fmtMoney', () {
    test('groups thousands, two decimals, ₪ suffix', () {
      expect(fmtMoney(1234567.5), '1,234,567.50 ₪');
    });

    test('decimals: false drops the fraction', () {
      expect(fmtMoney(1234, decimals: false), '1,234 ₪');
    });

    test('symbolLeft puts ₪ before the number', () {
      expect(fmtMoney(1234, symbolLeft: true), '₪1,234.00');
    });

    test('negative gets a leading minus', () {
      expect(fmtMoney(-50), '-50.00 ₪');
    });
  });

  group('fmtSigned', () {
    test('income gets a + prefix', () {
      expect(fmtSigned(100), '+100.00 ₪');
    });

    test('expense gets a − prefix', () {
      expect(fmtSigned(-100), '−100.00 ₪');
    });
  });

  group('fmtCompact', () {
    test('millions', () {
      expect(fmtCompact(1850000), '₪1.85M');
    });

    test('thousands', () {
      expect(fmtCompact(86400), '₪86.4K');
    });

    test('small values are whole', () {
      expect(fmtCompact(612), '₪612');
    });

    test('trims trailing zeros', () {
      expect(fmtCompact(2000000), '₪2M');
      expect(fmtCompact(10000000), '₪10M');
    });

    test('negative keeps the sign', () {
      expect(fmtCompact(-1850000), '-₪1.85M');
    });
  });
}
