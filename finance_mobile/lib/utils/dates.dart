/// Tolerant date parsing — mirrors the desktop `utils/dates.py`.
///
/// Movement dates *should* be ISO `YYYY-MM-DD` (the desktop now normalizes on
/// write), but older rows already in Firebase may still carry `dd/mm/yyyy`,
/// `dd.mm.yy`, or `dd-mm-yyyy`. Parse all of them so legacy data isn't silently
/// dropped from analytics or mis-sorted.
library;

/// Parse a date string in any format the app's data may contain. Returns null
/// when nothing matches.
DateTime? parseFlexibleDate(String value) {
  final s = value.trim();
  if (s.isEmpty) return null;

  // A bare `YYYY-MM` (month key) -> first of the month.
  if (RegExp(r'^\d{4}-\d{2}$').hasMatch(s)) {
    return DateTime.tryParse('$s-01');
  }

  // ISO fast path (YYYY-MM-DD, optionally with a time component).
  if (RegExp(r'^\d{4}-\d{2}-\d{2}').hasMatch(s)) {
    return DateTime.tryParse(s);
  }

  // Day-first with a `/`, `.` or `-` separator and a 2- or 4-digit year.
  final m = RegExp(r'^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2}|\d{4})$').firstMatch(s);
  if (m != null) {
    final day = int.parse(m.group(1)!);
    final month = int.parse(m.group(2)!);
    var year = int.parse(m.group(3)!);
    if (year < 100) year += 2000; // 2-digit years -> 20xx
    try {
      return DateTime(year, month, day);
    } catch (_) {
      return null;
    }
  }

  // Day/month without a year -> assume the current year.
  final m2 = RegExp(r'^(\d{1,2})[/.\-](\d{1,2})$').firstMatch(s);
  if (m2 != null) {
    try {
      return DateTime(DateTime.now().year, int.parse(m2.group(2)!),
          int.parse(m2.group(1)!));
    } catch (_) {
      return null;
    }
  }

  return null;
}

/// Normalize a date string to canonical ISO `YYYY-MM-DD`, or return the trimmed
/// original unchanged when it can't be parsed (never discards data).
String toIsoDate(String value) {
  final dt = parseFlexibleDate(value);
  if (dt == null) return value.trim();
  final mm = dt.month.toString().padLeft(2, '0');
  final dd = dt.day.toString().padLeft(2, '0');
  return '${dt.year}-$mm-$dd';
}
