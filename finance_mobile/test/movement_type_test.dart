import 'package:flutter_test/flutter_test.dart';
import 'package:finance_mobile/models/movement_type.dart';

void main() {
  group('MovementType.normalize', () {
    test('English canon passes through', () {
      expect(MovementType.normalize('MONTHLY'), MovementType.monthly);
      expect(MovementType.normalize('YEARLY'), MovementType.yearly);
      expect(MovementType.normalize('ONE_TIME'), MovementType.oneTime);
    });

    test('desktop Hebrew values map to the English canon', () {
      expect(MovementType.normalize('חודשי'), MovementType.monthly);
      expect(MovementType.normalize('שנתי'), MovementType.yearly);
      expect(MovementType.normalize('חד פעמי'), MovementType.oneTime);
    });

    test('case and variant insensitive', () {
      expect(MovementType.normalize('monthly'), MovementType.monthly);
      expect(MovementType.normalize('onetime'), MovementType.oneTime);
      expect(MovementType.normalize(' Yearly '), MovementType.yearly);
    });

    test('unknown / empty / null default to ONE_TIME', () {
      expect(MovementType.normalize(''), MovementType.oneTime);
      expect(MovementType.normalize(null), MovementType.oneTime);
      expect(MovementType.normalize('WEEKLY'), MovementType.oneTime);
    });
  });

  group('helpers', () {
    test('isMonthly recognizes both representations', () {
      expect(MovementType.isMonthly('MONTHLY'), isTrue);
      expect(MovementType.isMonthly('חודשי'), isTrue);
      expect(MovementType.isMonthly('YEARLY'), isFalse);
      expect(MovementType.isMonthly('שנתי'), isFalse);
    });

    test('label returns the Hebrew display value from either input', () {
      expect(MovementType.label('MONTHLY'), 'חודשי');
      expect(MovementType.label('חד פעמי'), 'חד פעמי');
    });
  });
}
