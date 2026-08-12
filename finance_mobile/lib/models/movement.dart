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
  // Transfer-only structured "what happened": the two accounts the money moved
  // between (null for income/expense, or for legacy transfers not yet backfilled).
  final String? transferFrom;
  final String? transferTo;
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
    this.transferFrom,
    this.transferTo,
    this.updatedAtMs,
  });

  /// Classify the movement: transfers first (they're not income/expense),
  /// otherwise by the amount sign.
  MovementKind get kind {
    if (isTransfer) return MovementKind.transfer;
    return amount >= 0 ? MovementKind.income : MovementKind.expense;
  }

  /// The transfer's source account: the structured field, else inferred from a
  /// legacy row (this leg's account is the source when money left it).
  String get transferSource =>
      transferFrom ?? (amount < 0 ? accountName : '');

  /// The transfer's target account (structured field, else inferred).
  String get transferTarget =>
      transferTo ?? (amount >= 0 ? accountName : '');

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
      'transfer_from': transferFrom,
      'transfer_to': transferTo,
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
    String? acct(String key) {
      final v = data[key];
      return (v is String && v.trim().isNotEmpty) ? v.trim() : null;
    }

    final transferFrom = acct('transfer_from');
    final transferTo = acct('transfer_to');
    // A transfer is flagged is_transfer, falls in the 'העברה' category, or
    // carries endpoints — mirror the desktop so both platforms classify the same.
    final isTransfer = ((data['is_transfer'] as bool?) ?? false) ||
        category.trim() == 'העברה' ||
        transferFrom != null ||
        transferTo != null;
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
      transferFrom: transferFrom,
      transferTo: transferTo,
      updatedAtMs: ms,
    );
  }
}


