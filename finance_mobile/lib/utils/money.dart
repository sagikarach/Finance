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
String fmtMoney(num v, {bool decimals = true}) {
  final neg = v < 0;
  final fixed = v.abs().toStringAsFixed(decimals ? 2 : 0);
  final dot = fixed.indexOf('.');
  final intPart = dot >= 0 ? fixed.substring(0, dot) : fixed;
  final frac = dot >= 0 ? fixed.substring(dot) : '';
  return '${neg ? '-' : ''}${_group(intPart)}$frac ₪';
}

/// Signed with an explicit +/- prefix (income vs expense).
String fmtSigned(num v) {
  final neg = v < 0;
  return '${neg ? '−' : '+'}${fmtMoney(v.abs())}';
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
  // Trim trailing .0 / .00
  if (body.contains('.')) {
    body = body.replaceFirst(RegExp(r'\.?0+([MK]?)$'), r'$1');
  }
  return '$neg₪$body';
}
