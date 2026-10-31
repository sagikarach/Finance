import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/movement.dart';

class MovementsCacheStore {
  const MovementsCacheStore();

  // Keyed by Firebase account *and* workspace: two accounts that share a
  // workspace (or one that typed another's code) never read each other's cache.
  static String _scope(String workspaceId) {
    final uid = (FirebaseAuth.instance.currentUser?.uid ?? '').trim();
    return '${uid.isEmpty ? '_local' : uid}:$workspaceId';
  }

  static String _movesKey(String workspaceId) =>
      'movements_cache_v2:${_scope(workspaceId)}';
  static String _watermarkKey(String workspaceId) =>
      'movements_cache_watermark_ms_v2:${_scope(workspaceId)}';

  Future<List<Movement>> loadMovements({required String workspaceId}) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_movesKey(workspaceId));
    if (raw == null || raw.trim().isEmpty) return <Movement>[];
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) return <Movement>[];
      return decoded
          .whereType<Map>()
          .map((m) => m.map((k, v) => MapEntry('$k', v)))
          .map((m) => Movement.fromFirestore(m))
          .where((m) => m.id.trim().isNotEmpty)
          .toList();
    } catch (_) {
      return <Movement>[];
    }
  }

  Future<void> saveMovements({
    required String workspaceId,
    required List<Movement> movements,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final data = movements
        .map((m) => <String, Object?>{
              'id': m.id,
              'amount': m.amount,
              'date': m.date,
              'account_name': m.accountName,
              'category': m.category,
              'type': m.type,
              'description': m.description,
              'event_id': m.eventId,
              'deleted': m.deleted,
              'updated_at_ms': m.updatedAtMs,
            })
        .toList();
    await prefs.setString(_movesKey(workspaceId), jsonEncode(data));
  }

  Future<int> loadWatermarkMs({required String workspaceId}) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_watermarkKey(workspaceId)) ?? 0;
  }

  Future<void> saveWatermarkMs({
    required String workspaceId,
    required int watermarkMs,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_watermarkKey(workspaceId), watermarkMs);
  }
}


