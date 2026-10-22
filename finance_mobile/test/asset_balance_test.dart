import 'package:flutter_test/flutter_test.dart';
import 'package:finance_mobile/services/assets_service.dart';

Map<String, dynamic> _house({Object? outstanding}) => {
      'id': 'h1',
      'name': 'דירה',
      'kind': 'נדל״ן',
      'property_price': 1000000,
      'tracks': [
        {'id': 't1', 'name': 'פריים', 'kind': 'פריים', 'principal': 600000},
        {'id': 't2', 'name': 'קל״צ', 'kind': 'קבועה', 'principal': 150000},
      ],
      if (outstanding != null) 'outstanding_balance': outstanding,
    };

void main() {
  group('Asset mortgage balance', () {
    test('uses the desktop-computed outstanding balance', () {
      final a = Asset.fromFirestore(_house(outstanding: 743340.5));
      expect(a.mortgageBalance, 743340.5);
      expect(a.equity, closeTo(256659.5, 1e-6));
      expect(AssetsService.netWorth([a]), closeTo(256659.5, 1e-6));
    });

    test('falls back to the original principal on older docs', () {
      final a = Asset.fromFirestore(_house());
      expect(a.outstandingBalance, isNull);
      expect(a.mortgageBalance, 750000);
      expect(a.equity, 250000);
    });

    test('a paid-off mortgage (0) is not treated as missing', () {
      final a = Asset.fromFirestore(_house(outstanding: 0));
      expect(a.mortgageBalance, 0);
      expect(a.equity, 1000000);
    });
  });
}
