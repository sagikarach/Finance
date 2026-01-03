import 'package:cloud_firestore/cloud_firestore.dart';

import '../models/movement.dart';
import 'movements_service.dart';

class AppNotification {
  final String id;
  final String key;
  final String type;
  final String title;
  final String message;
  final String severity;
  final String createdAt;
  final String status;
  final Map<String, dynamic> context;

  AppNotification({
    required this.id,
    required this.key,
    required this.type,
    required this.title,
    required this.message,
    required this.severity,
    required this.createdAt,
    required this.status,
    required this.context,
  });

  static AppNotification fromFirestore(Map<String, dynamic> data) {
    final rawCtx = data['context'];
    Map<String, dynamic> ctx = <String, dynamic>{};
    if (rawCtx is Map) {
      ctx = rawCtx.map((k, v) => MapEntry('$k', v));
    }
    return AppNotification(
      id: (data['id'] as String?) ?? '',
      key: (data['key'] as String?) ?? '',
      type: (data['type'] as String?) ?? '',
      title: (data['title'] as String?) ?? '',
      message: (data['message'] as String?) ?? '',
      severity: (data['severity'] as String?) ?? 'info',
      createdAt: (data['created_at'] as String?) ?? '',
      status: (data['status'] as String?) ?? 'unread',
      context: ctx,
    );
  }
}

class NotificationsService {
  final String workspaceId;
  final MovementsService _movements;

  NotificationsService({
    required this.workspaceId,
  }) : _movements = MovementsService(workspaceId: workspaceId);

  CollectionReference<Map<String, dynamic>> _ref() {
    return FirebaseFirestore.instance
        .collection('workspaces')
        .doc(workspaceId)
        .collection('notifications');
  }

  bool _isUnresolvedStatus(String status) {
    final s = status.trim().toLowerCase();
    return s != 'resolved' && s != 'dismissed';
  }

  Future<List<AppNotification>> fetchUnresolved({
    Source source = Source.server,
    int limit = 50,
  }) async {
    final snap = await _ref()
        .orderBy('created_at', descending: true)
        .limit(limit)
        .get(GetOptions(source: source));

    return snap.docs
        .map((d) => AppNotification.fromFirestore(d.data()))
        .where((n) => n.key.trim().isNotEmpty && _isUnresolvedStatus(n.status))
        .toList();
  }

  Future<Movement?> fetchMovementForDetails(AppNotification n) async {
    final ctx = n.context;
    final movementId = (ctx['movement_id'] as String?)?.trim() ?? '';
    if (movementId.isNotEmpty) {
      return await _fetchMovementById(movementId);
    }
    final ids = ctx['movement_ids'];
    if (ids is List && ids.isNotEmpty) {
      final first = (ids.first as String?)?.trim() ?? '';
      if (first.isNotEmpty) {
        return await _fetchMovementById(first);
      }
    }
    return null;
  }

  Future<Movement?> _fetchMovementById(String id) async {
    final mid = id.trim();
    if (mid.isEmpty) return null;
    final snap = await FirebaseFirestore.instance
        .collection('workspaces')
        .doc(workspaceId)
        .collection('movements')
        .doc(mid)
        .get(const GetOptions(source: Source.server));
    final data = snap.data();
    if (data == null) return null;
    final m = Movement.fromFirestore(data);
    if (m.id.trim().isEmpty || m.deleted) return null;
    return m;
  }
}


