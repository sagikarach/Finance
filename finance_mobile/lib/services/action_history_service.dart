import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:uuid/uuid.dart';

import '../models/movement.dart';
import 'session_service.dart';

class WorkspaceAction {
  final String id;
  final String timestamp; // YYYY-MM-DD
  final String? uid;
  final Map<String, dynamic> action;

  WorkspaceAction({
    required this.id,
    required this.timestamp,
    required this.uid,
    required this.action,
  });

  String get actionName => (action['action_name'] as String?)?.trim() ?? '';

  static WorkspaceAction fromFirestore(Map<String, dynamic> data) {
    final rawAction = data['action'];
    Map<String, dynamic> actionMap = <String, dynamic>{};
    if (rawAction is Map) {
      actionMap = rawAction.map((k, v) => MapEntry('$k', v));
    }
    return WorkspaceAction(
      id: (data['id'] as String?) ?? '',
      timestamp: (data['timestamp'] as String?) ?? '',
      uid: data['uid'] as String?,
      action: actionMap,
    );
  }
}

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

  Future<List<WorkspaceAction>> fetch({
    Source source = Source.server,
    int limit = 50,
  }) async {
    final snap = await _ref()
        .orderBy('timestamp', descending: true)
        .limit(limit)
        .get(GetOptions(source: source));

    return snap.docs
        .map((d) => WorkspaceAction.fromFirestore(d.data()))
        .where((a) => a.id.trim().isNotEmpty)
        .toList();
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

  Future<void> logEditSaving({
    required String savingsAccountName,
    required String savingName,
    required double oldAmount,
    required double newAmount,
    required String date,
  }) async {
    final actionId = const Uuid().v4();
    final today = DateTime.now().toIso8601String().split('T').first;
    final uid = _session.uid;
    final dateStr = date.trim().isEmpty ? today : date.trim();
    await _ref().doc(actionId).set(<String, Object?>{
      'id': actionId,
      'timestamp': today,
      if (uid != null) 'uid': uid,
      'action': <String, Object?>{
        'action_name': 'edit_saving',
        'account_name': savingsAccountName,
        'saving_name': savingName,
        'old_amount': oldAmount,
        'new_amount': newAmount,
        'date': dateStr,
      },
    }, SetOptions(merge: true));
  }
}


