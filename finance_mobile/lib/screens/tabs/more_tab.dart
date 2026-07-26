import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../../services/session_service.dart';
import '../../services/user_profile_service.dart';
import '../../theme/app_colors.dart';
import '../../widgets/ui/cards.dart';
import '../../widgets/ui/tab_top_bar.dart';
import '../../widgets/update_prompt.dart';
import '../account_switch_screen.dart';
import '../workspace_screen.dart';

class MoreTab extends StatelessWidget {
  final String workspaceId;
  final Listenable refresh;
  const MoreTab({super.key, required this.workspaceId, required this.refresh});

  @override
  Widget build(BuildContext context) {
    const session = SessionService();
    final user = FirebaseAuth.instance.currentUser;
    final email = (user?.email ?? '').trim();

    return Scaffold(
      backgroundColor: AppColors.screen,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            TabTopBar(
              title: 'עוד',
              workspaceId: workspaceId,
              showNotifications: false,
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 110),
                children: [
                  FutureBuilder<String>(
                    future: UserProfileService(workspaceId: workspaceId)
                        .fetchDisplayName(user?.uid ?? ''),
                    initialData:
                        UserProfileService.displayNameFromEmailFallback(),
                    builder: (context, snap) =>
                        _profileCard((snap.data ?? '').trim(), email),
                  ),
                  const SizedBox(height: 16),
                  AppCard(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Column(
                      children: [
                        _tile(Icons.group_rounded, 'החלף חשבון', () {
                          Navigator.of(context).push(MaterialPageRoute(
                              builder: (_) => const AccountSwitchScreen()));
                        }),
                        _divider(),
                        _tile(Icons.workspaces_rounded, 'סביבת עבודה ושיתוף',
                            () {
                          Navigator.of(context).push(MaterialPageRoute(
                              builder: (_) => const WorkspaceScreen()));
                        }),
                        _divider(),
                        _tile(Icons.system_update_rounded, 'בדוק עדכונים',
                            () => checkAndPromptUpdate(context, silent: false)),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  AppCard(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: _tile(
                      Icons.logout_rounded,
                      'התנתק',
                      () => session.signOut(),
                      danger: true,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _profileCard(String name, String email) {
    final initial = name.isNotEmpty
        ? name.characters.first
        : (email.isNotEmpty ? email.characters.first : '?');
    return AppCard(
      child: Row(
        children: [
          Container(
            width: 54,
            height: 54,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.lav,
              borderRadius: BorderRadius.circular(17),
            ),
            child: Text(initial,
                style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF3B3A63))),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name.isEmpty ? 'משתמש' : name,
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.w800)),
                if (email.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(email,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          color: AppColors.muted, fontSize: 12.5)),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _tile(IconData icon, String label, VoidCallback onTap,
      {bool danger = false}) {
    final color = danger ? AppColors.clay : AppColors.ink;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
        child: Row(
          children: [
            Icon(icon, size: 22, color: color),
            const SizedBox(width: 14),
            Expanded(
              child: Text(label,
                  style: TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w700, color: color)),
            ),
            if (!danger)
              const Icon(Icons.chevron_left_rounded,
                  color: AppColors.muted, size: 22),
          ],
        ),
      ),
    );
  }

  Widget _divider() => const Divider(
      height: 1,
      thickness: 1,
      color: AppColors.line,
      indent: 12,
      endIndent: 12);
}
