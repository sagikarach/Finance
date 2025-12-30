import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:uuid/uuid.dart';

import '../models/movement.dart';
import 'session_service.dart';

class ActionHistoryService {
  final String workspaceId;
  final SessionService _session;

  ActionHistoryService({
    required this.workspaceId,
    SessionService session = const SessionService(),
  }) : _session = session;

  CollectionReference<Map<String, dynamic>> _ref() {
    return FirebaseFirestore.instance
        .collection('workspaces')
        .doc(workspaceId)
        .collection('actions');
  }

  Future<void> logAddMovement({
    required String movementId,
    required bool isIncome,
  }) async {
    final actionId = const Uuid().v4();
    final today = DateTime.now().toIso8601String().split('T').first;
    final uid = _session.uid;
    await _ref().doc(actionId).set(<String, Object?>{
      'id': actionId,
      'timestamp': today,
      if (uid != null) 'uid': uid,
      'action': <String, Object?>{
        'action_name': isIncome ? 'add_income_movement' : 'add_outcome_movement',
        'movement_id': movementId,
      },
    }, SetOptions(merge: true));
  }

  Future<void> logDeleteMovement({required Movement m}) async {
    final actionId = const Uuid().v4();
    final today = DateTime.now().toIso8601String().split('T').first;
    final uid = _session.uid;
    await _ref().doc(actionId).set(<String, Object?>{
      'id': actionId,
      'timestamp': today,
      if (uid != null) 'uid': uid,
      'action': <String, Object?>{
        'action_name': 'delete_movement',
        'movement_id': m.id,
        'account_name': m.accountName,
        'amount': m.amount,
        'date': m.date,
      },
    }, SetOptions(merge: true));
  }
}


