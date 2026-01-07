import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AccountProfile {
  final String name;
  final String email;
  final String workspaceId;
  final int lastUsedAtMs;
  final bool rememberPassword;

  const AccountProfile({
    required this.name,
    required this.email,
    required this.workspaceId,
    required this.lastUsedAtMs,
    required this.rememberPassword,
  });

  Map<String, Object?> toJson() => <String, Object?>{
        'name': name,
        'email': email,
        'workspaceId': workspaceId,
        'lastUsedAtMs': lastUsedAtMs,
        'rememberPassword': rememberPassword,
      };

  static AccountProfile? fromJson(Object? raw) {
    if (raw is! Map) return null;
    final name = (raw['name'] as String?)?.trim() ?? '';
    final email = (raw['email'] as String?)?.trim() ?? '';
    if (email.isEmpty) return null;
    final workspaceId = (raw['workspaceId'] as String?)?.trim() ?? '';
    final lastUsedAtMs = (raw['lastUsedAtMs'] as int?) ?? 0;
    final rememberPassword = (raw['rememberPassword'] as bool?) ?? false;
    return AccountProfile(
      name: name,
      email: email,
      workspaceId: workspaceId,
      lastUsedAtMs: lastUsedAtMs,
      rememberPassword: rememberPassword,
    );
  }

  AccountProfile copyWith({
    String? name,
    String? email,
    String? workspaceId,
    int? lastUsedAtMs,
    bool? rememberPassword,
  }) {
    return AccountProfile(
      name: name ?? this.name,
      email: email ?? this.email,
      workspaceId: workspaceId ?? this.workspaceId,
      lastUsedAtMs: lastUsedAtMs ?? this.lastUsedAtMs,
      rememberPassword: rememberPassword ?? this.rememberPassword,
    );
  }
}

class AccountProfilesStore {
  static const _prefsKey = 'saved_accounts_v1';
  static const _pwPrefix = 'account_pw|';

  final FlutterSecureStorage _secure = const FlutterSecureStorage();

  Future<List<AccountProfile>> list() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_prefsKey) ?? '[]';
    final decoded = jsonDecode(raw);
    if (decoded is! List) return const <AccountProfile>[];
    final out = <AccountProfile>[];
    for (final item in decoded) {
      final p = AccountProfile.fromJson(item);
      if (p != null) out.add(p);
    }
    out.sort((a, b) {
      final d = b.lastUsedAtMs.compareTo(a.lastUsedAtMs);
      if (d != 0) return d;
      return a.email.toLowerCase().compareTo(b.email.toLowerCase());
    });
    return out;
  }

  Future<void> upsert({
    required String name,
    required String email,
    required String workspaceId,
    required bool rememberPassword,
  }) async {
    final n = name.trim();
    final e = email.trim();
    final wid = workspaceId.trim();
    if (e.isEmpty) return;
    final now = DateTime.now().millisecondsSinceEpoch;
    final items = await list();
    final updated = <AccountProfile>[];
    var found = false;
    for (final p in items) {
      if (_keyOf(p.email, p.workspaceId) == _keyOf(e, wid)) {
        updated.add(
          p.copyWith(
            name: n.isEmpty ? p.name : n,
            email: e,
            workspaceId: wid,
            lastUsedAtMs: now,
            rememberPassword: rememberPassword,
          ),
        );
        found = true;
      } else {
        updated.add(p);
      }
    }
    if (!found) {
      updated.add(AccountProfile(
        name: n,
        email: e,
        workspaceId: wid,
        lastUsedAtMs: now,
        rememberPassword: rememberPassword,
      ));
    }
    await _saveList(updated);
  }

  Future<void> delete(
      {required String email, required String workspaceId}) async {
    final e = email.trim();
    if (e.isEmpty) return;
    final wid = workspaceId.trim();
    final items = await list();
    final kept = items
        .where((p) => _keyOf(p.email, p.workspaceId) != _keyOf(e, wid))
        .toList();
    await _saveList(kept);
    await deletePassword(email: e, workspaceId: wid);
  }

  Future<void> touch(
      {required String email, required String workspaceId}) async {
    final e = email.trim();
    if (e.isEmpty) return;
    final wid = workspaceId.trim();
    final now = DateTime.now().millisecondsSinceEpoch;
    final items = await list();
    final updated = <AccountProfile>[];
    var changed = false;
    for (final p in items) {
      if (_keyOf(p.email, p.workspaceId) == _keyOf(e, wid)) {
        updated.add(p.copyWith(lastUsedAtMs: now));
        changed = true;
      } else {
        updated.add(p);
      }
    }
    if (changed) await _saveList(updated);
  }

  Future<void> setPassword({
    required String email,
    required String workspaceId,
    required String password,
  }) async {
    final e = email.trim();
    if (e.isEmpty) return;
    final wid = workspaceId.trim();
    await _secure.write(key: '$_pwPrefix${_keyOf(e, wid)}', value: password);
  }

  Future<String?> getPassword({
    required String email,
    required String workspaceId,
  }) async {
    final e = email.trim();
    if (e.isEmpty) return null;
    final wid = workspaceId.trim();
    String? v = await _secure.read(key: '$_pwPrefix${_keyOf(e, wid)}');
    v ??= await _secure.read(key: '$_pwPrefix$e'); // backward compat
    return (v == null || v.isEmpty) ? null : v;
  }

  Future<void> deletePassword({
    required String email,
    required String workspaceId,
  }) async {
    final e = email.trim();
    if (e.isEmpty) return;
    final wid = workspaceId.trim();
    await _secure.delete(key: '$_pwPrefix${_keyOf(e, wid)}');
    await _secure.delete(key: '$_pwPrefix$e'); // backward compat cleanup
  }

  Future<void> _saveList(List<AccountProfile> items) async {
    final prefs = await SharedPreferences.getInstance();
    final payload = items.map((p) => p.toJson()).toList();
    await prefs.setString(_prefsKey, jsonEncode(payload));
  }

  static String _keyOf(String email, String workspaceId) {
    final e = email.trim().toLowerCase();
    final w = workspaceId.trim();
    return '$e|$w';
  }
}
