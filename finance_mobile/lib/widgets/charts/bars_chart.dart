import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';

class BarDatum {
  final String label;
  final double value;
  final bool positive;
  final String? tooltip;
  const BarDatum({
    required this.label,
    required this.value,
    this.positive = true,
    this.tooltip,
  });
}

/// A row of rounded track+fill bars. Tapping a bar highlights it and shows its
/// tooltip; nothing is highlighted by default.
class BarsChart extends StatefulWidget {
  final List<BarDatum> data;
  final double height;

  const BarsChart({super.key, required this.data, this.height = 118});

  @override
  State<BarsChart> createState() => _BarsChartState();
}

class _BarsChartState extends State<BarsChart> {
  int? _selected;

  @override
  Widget build(BuildContext context) {
    final data = widget.data;
    return SizedBox(
      height: widget.height,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (var i = 0; i < data.length; i++)
            Expanded(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () =>
                    setState(() => _selected = _selected == i ? null : i),
                child: _bar(data[i], selected: i == _selected),
              ),
            ),
        ],
      ),
    );
  }

  Widget _bar(BarDatum d, {required bool selected}) {
    final maxV = widget.data.fold<double>(1, (m, e) => e.value > m ? e.value : m);
    return Column(
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
                      color: selected
                          ? AppColors.lav
                          : (d.positive ? AppColors.ink : AppColors.claySoft),
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  if (selected && d.tooltip != null)
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
          style: TextStyle(
            fontSize: 11,
            color: selected ? AppColors.ink : AppColors.muted,
            fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
          ),
        ),
      ],
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
        textDirection: TextDirection.ltr,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
