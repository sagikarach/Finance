import 'dart:math' as math;

import 'package:flutter/material.dart';

class DonutSegment {
  final double value;
  final Color color;
  const DonutSegment(this.value, this.color);
}

/// A rounded-segment donut with an optional widget in the center.
class DonutChart extends StatelessWidget {
  final List<DonutSegment> segments;
  final double size;
  final double thickness;
  final double gapDegrees;
  final Widget? center;

  const DonutChart({
    super.key,
    required this.segments,
    this.size = 200,
    this.thickness = 24,
    this.gapDegrees = 4,
    this.center,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size(size, size),
            painter: _DonutPainter(
              segments: segments,
              thickness: thickness,
              gapDegrees: gapDegrees,
            ),
          ),
          if (center != null) center!,
        ],
      ),
    );
  }
}

class _DonutPainter extends CustomPainter {
  final List<DonutSegment> segments;
  final double thickness;
  final double gapDegrees;

  _DonutPainter({
    required this.segments,
    required this.thickness,
    required this.gapDegrees,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final total =
        segments.fold<double>(0, (s, e) => s + (e.value <= 0 ? 0 : e.value));
    final rect = Rect.fromLTWH(
      thickness / 2,
      thickness / 2,
      size.width - thickness,
      size.height - thickness,
    );

    if (total <= 0) {
      final p = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = thickness
        ..color = const Color(0xFFECEAE2);
      canvas.drawArc(rect, 0, 2 * math.pi, false, p);
      return;
    }

    final gap = gapDegrees * math.pi / 180.0;
    final visible = segments.where((s) => s.value > 0).toList();
    var start = -math.pi / 2; // 12 o'clock
    for (final seg in visible) {
      final sweepFull = (seg.value / total) * 2 * math.pi;
      // Only inset by a gap when the slice is large enough to keep a visible arc.
      final useGap = visible.length > 1 && sweepFull > gap * 1.5;
      final sweep = useGap ? sweepFull - gap : sweepFull;
      final p = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = thickness
        ..strokeCap = useGap ? StrokeCap.round : StrokeCap.butt
        ..color = seg.color;
      canvas.drawArc(rect, start + (useGap ? gap / 2 : 0), sweep, false, p);
      start += sweepFull;
    }
  }

  @override
  bool shouldRepaint(covariant _DonutPainter old) =>
      old.segments != segments ||
      old.thickness != thickness ||
      old.gapDegrees != gapDegrees;
}
