import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../notifications_sheet.dart';

/// The top bar used by the secondary tabs: title on the (RTL) right, a
/// notifications bell and a sync button on the left.
class TabTopBar extends StatelessWidget {
  final String title;
  final bool syncing;
  final VoidCallback? onSync;
  final String workspaceId;
  final bool showNotifications;
  final IconData? extraIcon;
  final VoidCallback? onExtra;

  const TabTopBar({
    super.key,
    required this.title,
    required this.workspaceId,
    this.syncing = false,
    this.onSync,
    this.showNotifications = true,
    this.extraIcon,
    this.onExtra,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 8, 18, 8),
      child: Row(
        children: [
          Text(title,
              style:
                  const TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
          const Spacer(),
          if (extraIcon != null) ...[
            _btn(extraIcon!, onExtra, filled: true),
            const SizedBox(width: 8),
          ],
          if (showNotifications) ...[
            _btn(
                Icons.notifications_none_rounded,
                () => showNotificationsSheet(
                    context: context, workspaceId: workspaceId)),
            const SizedBox(width: 8),
          ],
          if (onSync != null || syncing)
            _btn(syncing ? Icons.hourglass_top_rounded : Icons.sync_rounded,
                syncing ? null : onSync),
        ],
      ),
    );
  }

  Widget _btn(IconData icon, VoidCallback? onTap, {bool filled = false}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: filled ? AppColors.ink : const Color(0xFFEFEDE4),
          borderRadius: BorderRadius.circular(13),
        ),
        child: Icon(icon,
            size: 20, color: filled ? Colors.white : AppColors.muted),
      ),
    );
  }
}
