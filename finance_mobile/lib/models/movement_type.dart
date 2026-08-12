/// Canonical movement types + tolerant normalization.
///
/// Firestore holds a mix of representations: the desktop app writes the Hebrew
/// enum values ('חודשי'/'שנתי'/'חד פעמי'), while the mobile app writes the
/// English keys ('MONTHLY'/'YEARLY'/'ONE_TIME'). Normalize both — and anything
/// unrecognized — to the English canon, mirroring the desktop's
/// parse_movement_type. Unknown/empty defaults to ONE_TIME.
class MovementType {
  MovementType._();

  static const monthly = 'MONTHLY';
  static const yearly = 'YEARLY';
  static const oneTime = 'ONE_TIME';

  /// Canonical key → Hebrew display label.
  static const labels = <String, String>{
    monthly: 'חודשי',
    yearly: 'שנתי',
    oneTime: 'חד פעמי',
  };

  /// Coerce any stored value (English or Hebrew, any case) to the canon.
  static String normalize(Object? raw) {
    final t = (raw?.toString() ?? '').trim();
    final upper = t.toUpperCase();
    if (upper == 'MONTHLY' || t == 'חודשי') return monthly;
    if (upper == 'YEARLY' || t == 'שנתי') return yearly;
    if (upper == 'ONE_TIME' || upper == 'ONETIME' || t == 'חד פעמי') {
      return oneTime;
    }
    return oneTime;
  }

  static String label(Object? raw) => labels[normalize(raw)]!;

  static bool isMonthly(Object? raw) => normalize(raw) == monthly;
}
