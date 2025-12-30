import 'package:cloud_firestore/cloud_firestore.dart';

import '../constants/accounts.dart';

class AccountsMetaService {
  final String workspaceId;

  AccountsMetaService({required this.workspaceId});

  DocumentReference<Map<String, dynamic>> _doc() {
    return FirebaseFirestore.instance
        .collection('workspaces')
        .doc(workspaceId)
        .collection('meta')
        .doc('accounts');
  }

  Future<void> ensureDoc() async {
    final ref = _doc();
    final snap = await ref.get();
    if (snap.exists) return;

    final bankAccounts = Accounts.fixedAccounts
        .map((name) => <String, Object?>{
              'name': name,
              'is_liquid': name == 'מזומן',
              'active': false,
            })
        .toList();

    await ref.set(<String, Object?>{
      'bank_accounts': bankAccounts,
      'savings_accounts': <Object?>[],
      'version': 1,
      'updated_at': FieldValue.serverTimestamp(),
    });
  }

  Future<void> ensureBankAccountExists(String name) async {
    final n = name.trim();
    if (n.isEmpty) return;

    final ref = _doc();
    final snap = await ref.get(const GetOptions(source: Source.server));
    final data = snap.data() ?? <String, dynamic>{};
    final raw = data['bank_accounts'];
    final List<Map<String, dynamic>> list = <Map<String, dynamic>>[];
    if (raw is List) {
      for (final it in raw) {
        if (it is Map) {
          list.add(it.map((k, v) => MapEntry('$k', v)));
        }
      }
    }

    final exists = list.any((x) => (x['name'] as String?) == n);
    if (exists) return;

    list.add(<String, Object?>{
      'name': n,
      'is_liquid': n == 'מזומן',
      'active': false,
    });

    await ref.set(<String, Object?>{
      'bank_accounts': list,
      'updated_at': FieldValue.serverTimestamp(),
      'version': 1,
    }, SetOptions(merge: true));
  }

  Future<List<String>> fetchActiveBankAccountNames({
    Source source = Source.server,
  }) async {
    final snap = await _doc().get(GetOptions(source: source));
    final data = snap.data() ?? <String, dynamic>{};
    final raw = data['bank_accounts'];
    final List<String> out = <String>[];
    if (raw is List) {
      for (final it in raw) {
        if (it is Map) {
          final m = it.map((k, v) => MapEntry('$k', v));
          final name = (m['name'] as String?)?.trim() ?? '';
          final active = (m['active'] as bool?) ?? false;
          if (name.isNotEmpty && active) out.add(name);
        }
      }
    }
    out.sort();
    return out;
  }

  Future<bool> isBankAccountActive({
    required String name,
    Source source = Source.server,
  }) async {
    final n = name.trim();
    if (n.isEmpty) return false;
    final snap = await _doc().get(GetOptions(source: source));
    final data = snap.data() ?? <String, dynamic>{};
    final raw = data['bank_accounts'];
    if (raw is List) {
      for (final it in raw) {
        if (it is Map) {
          final m = it.map((k, v) => MapEntry('$k', v));
          if ((m['name'] as String?) == n) {
            return (m['active'] as bool?) ?? false;
          }
        }
      }
    }
    return false;
  }

  Future<Map<String, dynamic>?> fetchBankAccountRow({
    required String name,
    Source source = Source.server,
  }) async {
    final n = name.trim();
    if (n.isEmpty) return null;
    final snap = await _doc().get(GetOptions(source: source));
    final data = snap.data() ?? <String, dynamic>{};
    final raw = data['bank_accounts'];
    if (raw is List) {
      for (final it in raw) {
        if (it is Map) {
          final m = it.map((k, v) => MapEntry('$k', v));
          if ((m['name'] as String?)?.trim() == n) {
            return m;
          }
        }
      }
    }
    return null;
  }
}


