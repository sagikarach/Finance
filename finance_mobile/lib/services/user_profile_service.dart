import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Reads the per-user profile the desktop syncs to
/// `workspaces/{wid}/users/{uid}` (see desktop upsert_user_profile → full_name).
class UserProfileService {
  final String workspaceId;

  static const _prefsKey = 'user_display_name';

  UserProfileService({required this.workspaceId});

  Future<String> fetchFullName(String uid,
      {Source source = Source.server}) async {
    if (uid.trim().isEmpty) return '';
    try {
      final snap = await FirebaseFirestore.instance
          .collection('workspaces')
          .doc(workspaceId)
          .collection('users')
          .doc(uid)
          .get(GetOptions(source: source));
      return (snap.data()?['full_name'] as String?)?.trim() ?? '';
    } catch (_) {
      return '';
    }
  }

  /// The last resolved name, persisted locally so the greeting shows it
  /// immediately on the next launch (no wrong-name flash while the network
  /// fetch is in flight).
  Future<String> loadCachedName() async {
    try {
      final p = await SharedPreferences.getInstance();
      return (p.getString(_prefsKey) ?? '').trim();
    } catch (_) {
      return '';
    }
  }

  Future<void> _saveName(String name) async {
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_prefsKey, name);
    } catch (_) {}
  }

  /// Best display name available: the synced full name (Firestore cache first,
  /// then server), else a friendly form of the account email. The resolved
  /// name is persisted for instant display next time.
  Future<String> fetchDisplayName(String uid) async {
    var full = await fetchFullName(uid, source: Source.cache);
    if (full.isEmpty) full = await fetchFullName(uid, source: Source.server);
    if (full.isNotEmpty) {
      await _saveName(full);
      return full;
    }
    return displayNameFromEmailFallback();
  }

  static String displayNameFromEmailFallback() {
    final email = FirebaseAuth.instance.currentUser?.email?.trim() ?? '';
    if (email.isEmpty) return '';
    final local = email.split('@').first;
    final first = local.split(RegExp(r'[._-]')).firstWhere(
          (s) => s.isNotEmpty,
          orElse: () => local,
        );
    if (first.isEmpty) return '';
    return first[0].toUpperCase() + first.substring(1);
  }
}
