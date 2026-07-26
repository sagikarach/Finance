import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

/// Reads the per-user profile the desktop syncs to
/// `workspaces/{wid}/users/{uid}` (see desktop upsert_user_profile → full_name).
class UserProfileService {
  final String workspaceId;

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

  /// Best display name available: the synced full name, else a friendly form of
  /// the account email, else empty.
  Future<String> fetchDisplayName(String uid,
      {Source source = Source.server}) async {
    final full = await fetchFullName(uid, source: source);
    if (full.isNotEmpty) return full;
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
