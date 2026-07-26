import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';

class BarDatum {
  final String label;
  final double value;
  final bool highlight;
  final String? tooltip;
  const BarDatum({
    required this.label,
    required this.value,
    this.highlight = false,
    this.tooltip,
  });
}

/// A row of rounded track+fill bars (like the reference weekly chart).
class BarsChart extends StatelessWidget {
  final List<BarDatum> data;
  final double height;

  const BarsChart({super.key, required this.data, this.height = 118});

  @override
  Widget build(BuildContext context) {
    final maxV = data.fold<double>(1, (m, d) => d.value > m ? d.value : m);
    return SizedBox(
      height: height,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (final d in data)
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Expanded(
                    child: LayoutBuilder(
                      builder: (context, c) {
                        final frac = (d.value / maxV).clamp(0.04, 1.0);
                        final fillH = c.maxHeight * frac;
                        return Stack(
                          alignment: Alignment.bottomCenter,
                          clipBehavior: Clip.none,
                          children: [
                            Container(
                              width: 16,
                              height: c.maxHeight,
                              decoration: BoxDecoration(
                                color: const Color(0xFFEFEDE4),
                                borderRadius: BorderRadius.circular(10),
                              ),
                            ),
                            Container(
                              width: 16,
                              height: fillH,
                              decoration: BoxDecoration(
                                color:
                                    d.highlight ? AppColors.lav : AppColors.ink,
                                borderRadius: BorderRadius.circular(10),
                              ),
                            ),
                            if (d.highlight && d.tooltip != null)
                              Positioned(
                                bottom: fillH + 6,
                                child: _Tooltip(text: d.tooltip!),
                              ),
                          ],
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    d.label,
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.muted,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _Tooltip extends StatelessWidget {
  final String text;
  const _Tooltip({required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.ink,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        text,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
