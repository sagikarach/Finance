import 'package:cloud_firestore/cloud_firestore.dart';

class Movement {
  final String id;
  final double amount; // +income, -expense
  final String date; // YYYY-MM-DD
  final String accountName;
  final String category;
  final String type; // MONTHLY | YEARLY | ONE_TIME
  final String? description;
  final String? eventId;
  final bool deleted;
  final int? updatedAtMs;

  Movement({
    required this.id,
    required this.amount,
    required this.date,
    required this.accountName,
    required this.category,
    required this.type,
    this.description,
    this.eventId,
    this.deleted = false,
    this.updatedAtMs,
  });

  Map<String, Object?> toFirestore() {
    final nowMs = DateTime.now().millisecondsSinceEpoch;
    return <String, Object?>{
      'id': id,
      'amount': amount,
      'date': date,
      'account_name': accountName,
      'category': category,
      'type': type,
      'description': description,
      'event_id': eventId,
      'deleted': deleted,
      'source': 'mobile',
      'created_at': FieldValue.serverTimestamp(),
      'updated_at': FieldValue.serverTimestamp(),
      // Cross-platform incremental pull watermark.
      'created_at_ms': nowMs,
      'updated_at_ms': nowMs,
    };
  }

  static Movement fromFirestore(Map<String, dynamic> data) {
    int? ms;
    final rawMs = data['updated_at_ms'];
    if (rawMs is int) ms = rawMs;
    if (rawMs is num) ms = rawMs.toInt();
    return Movement(
      id: (data['id'] as String?) ?? '',
      amount: (data['amount'] as num?)?.toDouble() ?? 0.0,
      date: (data['date'] as String?) ?? '',
      accountName: (data['account_name'] as String?) ?? '',
      category: (data['category'] as String?) ?? '',
      type: (data['type'] as String?) ?? 'ONE_TIME',
      description: data['description'] as String?,
      eventId: data['event_id'] as String?,
      deleted: (data['deleted'] as bool?) ?? false,
      updatedAtMs: ms,
    );
  }
}


