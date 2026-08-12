import 'package:flutter_test/flutter_test.dart';
import 'package:finance_mobile/models/movement.dart';

void main() {
  group('Movement.fromFirestore', () {
    test('parses a full document', () {
      final m = Movement.fromFirestore({
        'id': 'a',
        'amount': -100.5,
        'date': '2026-01-05',
        'account_name': 'בנק',
        'category': 'מזון',
        'type': 'MONTHLY',
        'description': 'קניות',
        'event_id': 'e1',
        'deleted': false,
        'updated_at_ms': 1234,
      });
      expect(m.id, 'a');
      expect(m.amount, -100.5);
      expect(m.date, '2026-01-05');
      expect(m.accountName, 'בנק');
      expect(m.category, 'מזון');
      expect(m.type, 'MONTHLY');
      expect(m.description, 'קניות');
      expect(m.eventId, 'e1');
      expect(m.deleted, false);
      expect(m.updatedAtMs, 1234);
    });

    test('applies defaults for a sparse document', () {
      final m = Movement.fromFirestore(<String, dynamic>{});
      expect(m.id, '');
      expect(m.amount, 0.0);
      expect(m.date, '');
      expect(m.accountName, '');
      expect(m.category, '');
      expect(m.type, 'ONE_TIME'); // missing type defaults to ONE_TIME
      expect(m.description, isNull);
      expect(m.eventId, isNull);
      expect(m.deleted, false);
      expect(m.updatedAtMs, isNull);
    });

    test('coerces an int amount to double', () {
      final m = Movement.fromFirestore({'id': 'a', 'amount': 5});
      expect(m.amount, 5.0);
      expect(m.amount, isA<double>());
    });

    test('coerces a num updated_at_ms to int', () {
      final m = Movement.fromFirestore({'id': 'a', 'updated_at_ms': 1700.0});
      expect(m.updatedAtMs, 1700);
    });

    test('honours deleted = true', () {
      final m = Movement.fromFirestore({'id': 'a', 'deleted': true});
      expect(m.deleted, true);
    });

    test('normalizes a desktop Hebrew type to the English canon', () {
      // desktop writes the Hebrew enum value; mobile must read it as MONTHLY
      final m = Movement.fromFirestore({'id': 'a', 'type': 'חודשי'});
      expect(m.type, 'MONTHLY');
    });
  });

  group('Movement.toFirestore', () {
    test('maps the plain fields and tags source = mobile', () {
      final m = Movement(
        id: 'a',
        amount: -10,
        date: '2026-01-01',
        accountName: 'בנק',
        category: 'מזון',
        type: 'ONE_TIME',
        description: 'קניות',
        eventId: null,
        deleted: false,
      );
      final map = m.toFirestore();
      expect(map['id'], 'a');
      expect(map['amount'], -10);
      expect(map['date'], '2026-01-01');
      expect(map['account_name'], 'בנק');
      expect(map['category'], 'מזון');
      expect(map['type'], 'ONE_TIME');
      expect(map['description'], 'קניות');
      expect(map['event_id'], isNull);
      expect(map['deleted'], false);
      expect(map['source'], 'mobile');
      // watermark is set for incremental cross-platform pulls
      expect(map['updated_at_ms'], isA<int>());
    });
  });
}
