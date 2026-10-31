import 'dart:math';

import 'package:cloud_firestore/cloud_firestore.dart';

class WorkspaceService {
  final _db = FirebaseFirestore.instance;

  Future<String?> getActiveWorkspaceId(String uid) async {
    final snap = await _db.collection('users').doc(uid).get();
    final data = snap.data();
    final wid = (data?['active_workspace_id'] as String?)?.trim();
    return (wid == null || wid.isEmpty) ? null : wid;
  }

  Future<void> setActiveWorkspaceId(String uid, String wid) async {
    await _db.collection('users').doc(uid).set(
      <String, Object?>{'active_workspace_id': wid},
      SetOptions(merge: true),
    );
  }

  /// Adds [uid] to workspace [wid] (creating the workspace when it doesn't
  /// exist yet). Order matters for firestore.rules: the member doc is written
  /// first, because only members may update the workspace doc. An existing
  /// membership keeps its role, and an existing workspace keeps its creator.
  Future<void> ensureMembership({
    required String uid,
    required String wid,
    required String role,
  }) async {
    final wsRef = _db.collection('workspaces').doc(wid);
    final memberRef = wsRef.collection('members').doc(uid);

    final memberSnap = await memberRef.get();
    if (!memberSnap.exists) {
      await memberRef.set(<String, Object?>{
        'role': role,
        'joined_at': FieldValue.serverTimestamp(),
      });
    }

    final wsSnap = await wsRef.get();
    if (!wsSnap.exists) {
      await wsRef.set(<String, Object?>{
        'version': 1,
        'created_by': uid,
        'updated_at': FieldValue.serverTimestamp(),
      });
    } else {
      await wsRef.set(
        <String, Object?>{'updated_at': FieldValue.serverTimestamp()},
        SetOptions(merge: true),
      );
    }
  }

  Future<void> validateWorkspaceExists(String wid) async {
    final snap = await _db.collection('workspaces').doc(wid).get();
    if (!snap.exists) {
      throw Exception('קוד שיתוף לא תקין');
    }
  }

  String generateWorkspaceCode() {
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    final rnd = Random.secure();
    final raw = List.generate(12, (_) => alphabet[rnd.nextInt(alphabet.length)]).join();
    return '${raw.substring(0, 4)}-${raw.substring(4, 8)}-${raw.substring(8, 12)}';
  }
}


