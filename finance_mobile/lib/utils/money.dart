// Shared money formatting so every screen renders amounts the same way.

String _group(String intPart) {
  final buf = StringBuffer();
  for (var i = 0; i < intPart.length; i++) {
    if (i > 0 && (intPart.length - i) % 3 == 0) buf.write(',');
    buf.write(intPart[i]);
  }
  return buf.toString();
}

/// e.g. 1,234,567.50 ₪ — grouped thousands, two decimals, ₪ suffix.
/// With [symbolLeft], the ₪ is a prefix (₪1,234) so that in an LTR-rendered
/// widget the symbol still sits to the left of the number.
String fmtMoney(num v, {bool decimals = true, bool symbolLeft = false}) {
  final neg = v < 0;
  final fixed = v.abs().toStringAsFixed(decimals ? 2 : 0);
  final dot = fixed.indexOf('.');
  final intPart = dot >= 0 ? fixed.substring(0, dot) : fixed;
  final frac = dot >= 0 ? fixed.substring(dot) : '';
  final number = '${_group(intPart)}$frac';
  final sign = neg ? '-' : '';
  return symbolLeft ? '$sign₪$number' : '$sign$number ₪';
}

/// Signed with an explicit +/- prefix (income vs expense).
String fmtSigned(num v, {bool decimals = true, bool symbolLeft = false}) {
  final neg = v < 0;
  final sign = neg ? '−' : '+';
  return '$sign${fmtMoney(v.abs(), decimals: decimals, symbolLeft: symbolLeft)}';
}

/// Compact hero form: ₪1.85M / ₪86.4K / ₪612.
String fmtCompact(num v) {
  final a = v.abs();
  final neg = v < 0 ? '-' : '';
  String body;
  if (a >= 1000000) {
    body = '${(a / 1000000).toStringAsFixed(a >= 10000000 ? 1 : 2)}M';
  } else if (a >= 1000) {
    body = '${(a / 1000).toStringAsFixed(a >= 100000 ? 0 : 1)}K';
  } else {
    body = a.toStringAsFixed(0);
  }
  // Trim trailing .0 / .00 while keeping the M/K suffix. Uses ...Mapped because
  // Dart's replaceFirst treats "$1" as a literal, not a capture-group reference.
  if (body.contains('.')) {
    body = body.replaceFirstMapped(
      RegExp(r'\.?0+([MK]?)$'),
      (m) => m.group(1) ?? '',
    );
  }
  return '$neg₪$body';
}
