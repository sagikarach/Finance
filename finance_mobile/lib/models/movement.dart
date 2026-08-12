import 'package:cloud_firestore/cloud_firestore.dart';
import 'movement_type.dart';

/// The kind of money-movement, independent of the recurrence [type]:
/// הכנסה (income), הוצאה (expense), or העברה (transfer between own accounts).
enum MovementKind { income, expense, transfer }

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
  final bool isTransfer; // העברה — not real income/expense
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
    this.isTransfer = false,
    this.updatedAtMs,
  });

  /// Classify the movement: transfers first (they're not income/expense),
  /// otherwise by the amount sign.
  MovementKind get kind {
    if (isTransfer) return MovementKind.transfer;
    return amount >= 0 ? MovementKind.income : MovementKind.expense;
  }

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
      'is_transfer': isTransfer,
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
    final category = (data['category'] as String?) ?? '';
    // A transfer is flagged is_transfer, or falls in the 'העברה' category —
    // mirror the desktop so cross-platform data classifies the same way.
    final isTransfer =
        ((data['is_transfer'] as bool?) ?? false) || category.trim() == 'העברה';
    return Movement(
      id: (data['id'] as String?) ?? '',
      amount: (data['amount'] as num?)?.toDouble() ?? 0.0,
      date: (data['date'] as String?) ?? '',
      accountName: (data['account_name'] as String?) ?? '',
      category: category,
      // Desktop stores Hebrew type values, mobile English — canonicalize both.
      type: MovementType.normalize(data['type']),
      description: data['description'] as String?,
      eventId: data['event_id'] as String?,
      deleted: (data['deleted'] as bool?) ?? false,
      isTransfer: isTransfer,
      updatedAtMs: ms,
    );
  }
}


