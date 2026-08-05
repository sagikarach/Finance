import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Does this subtree contain a Transform that flips horizontally (scaleX < 0)?
bool _hasHorizontalFlip(WidgetTester tester) {
  for (final t in tester.widgetList<Transform>(find.byType(Transform))) {
    // storage index 0 is the x-scale for a simple scale matrix.
    if (t.transform.storage[0] < 0) return true;
  }
  return false;
}

void main() {
  testWidgets('chevron mirrors under RTL, but not when forced LTR',
      (tester) async {
    // Baseline: chevron_left inside RTL -> should be mirrored (flip transform).
    await tester.pumpWidget(const Directionality(
      textDirection: TextDirection.rtl,
      child: Icon(Icons.chevron_left),
    ));
    final mirroredUnderRtl = _hasHorizontalFlip(tester);

    // Fix: same icon inside RTL but Icon forced to LTR -> should NOT mirror.
    await tester.pumpWidget(const Directionality(
      textDirection: TextDirection.rtl,
      child: Icon(Icons.chevron_left, textDirection: TextDirection.ltr),
    ));
    final mirroredWithFix = _hasHorizontalFlip(tester);

    expect(mirroredUnderRtl, isTrue,
        reason: 'chevron_left should mirror under RTL (matchTextDirection)');
    expect(mirroredWithFix, isFalse,
        reason: 'forcing Icon textDirection ltr must stop the mirror');
  });
}
