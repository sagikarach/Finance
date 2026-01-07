import 'package:cloud_firestore/cloud_firestore.dart';

import '../models/movement.dart';
import 'movements_cache_store.dart';

class MovementsService {
  final String workspaceId;
  final MovementsCacheStore _cache;

  MovementsService({
    required this.workspaceId,
    MovementsCacheStore cache = const MovementsCacheStore(),
  }) : _cache = cache;

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

  Future<List<Movement>> fetchIncremental() async {
    // 1) Load cache for immediate baseline.
    final cached = await _cache.loadMovements(workspaceId: workspaceId);
    final byId = <String, Movement>{for (final m in cached) m.id: m};
    var watermarkMs = await _cache.loadWatermarkMs(workspaceId: workspaceId);

    // 2) First run (no watermark) => full pull once.
    if (watermarkMs <= 0) {
      final full = await fetch(source: Source.server);
      final nowMs = DateTime.now().millisecondsSinceEpoch;
      final maxMs = full
          .map((m) => m.updatedAtMs ?? 0)
          .fold<int>(0, (a, b) => a > b ? a : b);
      await _cache.saveMovements(workspaceId: workspaceId, movements: full);
      await _cache.saveWatermarkMs(
          workspaceId: workspaceId, watermarkMs: maxMs > 0 ? maxMs : nowMs);
      return full;
    }

    // 3) Pull only updates.
    final snap = await _ref()
        .where('updated_at_ms', isGreaterThan: watermarkMs)
        .orderBy('updated_at_ms', descending: false)
        .get(const GetOptions(source: Source.server));

    var maxSeenMs = watermarkMs;
    for (final d in snap.docs) {
      final m = Movement.fromFirestore(d.data());
      if (m.id.trim().isEmpty) continue;
      byId[m.id] = m;
      final ms = m.updatedAtMs ?? 0;
      if (ms > maxSeenMs) maxSeenMs = ms;
    }

    final merged = byId.values
        .where((m) => m.id.isNotEmpty)
        .toList()
      ..sort((a, b) => b.date.compareTo(a.date));

    await _cache.saveMovements(workspaceId: workspaceId, movements: merged);
    if (maxSeenMs > watermarkMs) {
      await _cache.saveWatermarkMs(workspaceId: workspaceId, watermarkMs: maxSeenMs);
    }

    return merged.where((m) => !m.deleted).toList();
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
      'updated_at_ms': DateTime.now().millisecondsSinceEpoch,
    }, SetOptions(merge: true));
  }
}


