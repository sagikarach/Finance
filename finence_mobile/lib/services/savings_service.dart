import 'package:cloud_firestore/cloud_firestore.dart';

class SavingsService {
  final String workspaceId;

  SavingsService({required this.workspaceId});

  DocumentReference<Map<String, dynamic>> _doc() {
    return FirebaseFirestore.instance
        .collection('workspaces')
        .doc(workspaceId)
        .collection('meta')
        .doc('accounts');
  }

  Future<List<Map<String, dynamic>>> fetchSavingsAccountsRaw({
    Source source = Source.server,
  }) async {
    final snap = await _doc().get(GetOptions(source: source));
    final data = snap.data() ?? <String, dynamic>{};
    final raw = data['savings_accounts'];
    final out = <Map<String, dynamic>>[];
    if (raw is List) {
      for (final it in raw) {
        if (it is Map) {
          out.add(it.map((k, v) => MapEntry('$k', v)));
        }
      }
    }
    return out;
  }

  Future<void> editSaving({
    required String savingsAccountName,
    required String savingName,
    required double newAmount,
    required String date,
  }) async {
    final accName = savingsAccountName.trim();
    final sName = savingName.trim();
    if (accName.isEmpty) throw Exception('שם חשבון חסכון ריק');
    if (sName.isEmpty) throw Exception('שם חסכון ריק');
    if (!newAmount.isFinite) throw Exception('סכום לא חוקי');

    final today = DateTime.now().toIso8601String().split('T').first;
    final dateStr = date.trim().isEmpty ? today : date.trim();

    final ref = _doc();
    final snap = await ref.get(const GetOptions(source: Source.server));
    final data = snap.data() ?? <String, dynamic>{};
    final raw = data['savings_accounts'];

    final List<Map<String, dynamic>> accounts = <Map<String, dynamic>>[];
    if (raw is List) {
      for (final it in raw) {
        if (it is Map) {
          accounts.add(it.map((k, v) => MapEntry('$k', v)));
        }
      }
    }

    final accIdx = accounts.indexWhere(
      (m) => (m['name'] as String?)?.trim() == accName,
    );
    if (accIdx < 0) {
      throw Exception('לא נמצא חשבון חסכון בשם "$accName"');
    }

    final acc = Map<String, dynamic>.from(accounts[accIdx]);
    final rawSavings = acc['savings'];
    final List<Map<String, dynamic>> savings = <Map<String, dynamic>>[];
    if (rawSavings is List) {
      for (final it in rawSavings) {
        if (it is Map) {
          savings.add(it.map((k, v) => MapEntry('$k', v)));
        }
      }
    }

    final sIdx = savings.indexWhere(
      (m) => (m['name'] as String?)?.trim() == sName,
    );
    if (sIdx < 0) {
      throw Exception('לא נמצא חסכון בשם "$sName"');
    }

    final saving = Map<String, dynamic>.from(savings[sIdx]);
    saving['amount'] = newAmount;

    final rawHist = saving['history'];
    final List<Map<String, dynamic>> hist = <Map<String, dynamic>>[];
    if (rawHist is List) {
      for (final it in rawHist) {
        if (it is Map) {
          hist.add(it.map((k, v) => MapEntry('$k', v)));
        }
      }
    }
    hist.add(<String, Object?>{'date': dateStr, 'amount': newAmount});
    saving['history'] = hist;

    savings[sIdx] = saving;
    acc['savings'] = savings;

    double total = 0.0;
    for (final s in savings) {
      final a = s['amount'];
      if (a is num) total += a.toDouble();
    }
    acc['total_amount'] = total;

    accounts[accIdx] = acc;

    await ref.set(<String, Object?>{
      'savings_accounts': accounts,
      'updated_at': FieldValue.serverTimestamp(),
      'version': 1,
    }, SetOptions(merge: true));
  }
}


