import 'package:flutter/material.dart';

import '../../models/movement.dart';
import '../../theme/app_colors.dart';
import '../../utils/money.dart';

/// Pick an icon + tint for a movement based on its category text.
({IconData icon, Color color}) categoryVisual(String category, bool income) {
  final c = category.trim();
  bool has(List<String> kws) => kws.any((k) => c.contains(k));

  if (income) return (icon: Icons.trending_up_rounded, color: AppColors.green);
  if (has(['שכר', 'משכורת', 'הכנסה'])) {
    return (icon: Icons.work_rounded, color: AppColors.sage);
  }
  if (has(['דיור', 'שכירות', 'משכנתא', 'ארנונה', 'דירה'])) {
    return (icon: Icons.home_rounded, color: AppColors.claySoft);
  }
  if (has(['מזון', 'סופר', 'מרקט', 'אוכל', 'מסעד'])) {
    return (icon: Icons.shopping_cart_rounded, color: AppColors.yellow);
  }
  if (has(['רכב', 'דלק', 'תחבורה', 'חניה', 'אוטובוס'])) {
    return (icon: Icons.directions_car_rounded, color: AppColors.lav);
  }
  if (has(['פנאי', 'בילוי', 'מסעדה', 'קפה', 'סרט'])) {
    return (icon: Icons.local_cafe_rounded, color: AppColors.claySoft);
  }
  if (has(['חשמל', 'מים', 'גז', 'תקשורת', 'אינטרנט', 'טלפון'])) {
    return (icon: Icons.bolt_rounded, color: AppColors.sage);
  }
  return (icon: Icons.receipt_long_rounded, color: AppColors.lav);
}

class TxTile extends StatelessWidget {
  final Movement movement;
  final VoidCallback? onTap;

  const TxTile({super.key, required this.movement, this.onTap});

  @override
  Widget build(BuildContext context) {
    final m = movement;
    final income = m.amount >= 0;
    final v = categoryVisual(m.category, income);
    final title = (m.description?.trim().isNotEmpty ?? false)
        ? m.description!.trim()
        : (m.category.trim().isNotEmpty ? m.category.trim() : 'תנועה');
    final sub = [
      if (m.date.trim().isNotEmpty) m.date.trim(),
      if (m.category.trim().isNotEmpty) m.category.trim(),
    ].join(' · ');

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(20),
        boxShadow: const [
          BoxShadow(
              color: Color(0x1220280F), blurRadius: 18, offset: Offset(0, 8)),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: v.color.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(13),
            ),
            child: Icon(v.icon, size: 20, color: _darken(v.color)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 14),
                ),
                if (sub.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    sub,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style:
                        const TextStyle(color: AppColors.muted, fontSize: 11.5),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            fmtSigned(m.amount, decimals: false),
            textDirection: TextDirection.ltr,
            style: TextStyle(
              color: income ? AppColors.green : AppColors.clay,
              fontWeight: FontWeight.w800,
              fontSize: 14.5,
            ),
          ),
        ],
      ),
    );
  }

  static Color _darken(Color c) =>
      Color.alphaBlend(c.withValues(alpha: 0.85), AppColors.ink);
}
