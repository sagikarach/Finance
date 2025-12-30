import 'package:cloud_firestore/cloud_firestore.dart';

import '../models/movement.dart';

class MovementsService {
  final String workspaceId;

  MovementsService({required this.workspaceId});

  CollectionReference<Map<String, dynamic>> _ref() {
    return FirebaseFirestore.instance
        .collection('workspaces')
        .doc(workspaceId)
        .collection('movements');
  }

  Future<List<Movement>> fetch({Source source = Source.server}) async {
    final snap = await _ref()
        .orderBy('date', descending: true)
        .get(GetOptions(source: source));

    return snap.docs
        .map((d) => Movement.fromFirestore(d.data()))
        .where((m) => m.id.isNotEmpty && !m.deleted)
        .toList();
  }

  Future<void> upsert(Movement m) async {
    if (m.id.trim().isEmpty) return;
    await _ref().doc(m.id).set(m.toFirestore(), SetOptions(merge: true));
  }

  Future<void> tombstoneDelete({required String movementId}) async {
    final id = movementId.trim();
    if (id.isEmpty) return;
    await _ref().doc(id).set(<String, Object?>{
      'id': id,
      'deleted': true,
      'updated_at': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }
}


