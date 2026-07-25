import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path_provider/path_provider.dart';

/// In-app updater for the mobile app — the analog of the desktop `updater.py`.
///
/// Both apps publish GitHub Releases in the same repo, so (exactly like the
/// desktop updater) we must NOT use `/releases/latest` — a `desktop-v*` release
/// could be the repo-wide latest. Instead we list releases and pick the newest
/// **mobile** one (tag `mobile-v*`), then download its `.apk` asset.
///
/// Android can download + launch the system installer. iOS cannot self-install
/// (App Store only), so there we only surface the release page.
class UpdateInfo {
  final String version; // e.g. "0.2.0"
  final String tag; // e.g. "mobile-v0.2.0"
  final String? apkUrl; // browser_download_url of the .apk asset (Android)
  final String releaseUrl; // html_url of the release (fallback / iOS)
  final String notes; // release body

  const UpdateInfo({
    required this.version,
    required this.tag,
    required this.apkUrl,
    required this.releaseUrl,
    required this.notes,
  });
}

class UpdateService {
  static const String repo = 'sagikarach/Finance';

  const UpdateService();

  /// The bare version of the running app (from the platform package info).
  Future<String> currentVersion() async {
    try {
      final info = await PackageInfo.fromPlatform();
      return info.version; // "0.2.0" (without the +build)
    } catch (_) {
      return '0.0.0';
    }
  }

  /// Returns an [UpdateInfo] when a newer mobile release exists, else null.
  Future<UpdateInfo?> checkForUpdate() async {
    final current = await currentVersion();
    final uri = Uri.parse(
      'https://api.github.com/repos/$repo/releases?per_page=30',
    );
    final resp = await http.get(
      uri,
      headers: const {'Accept': 'application/vnd.github+json'},
    ).timeout(const Duration(seconds: 20));
    if (resp.statusCode != 200) {
      throw HttpException('GitHub API ${resp.statusCode}');
    }
    final releases = (jsonDecode(resp.body) as List).cast<dynamic>();

    for (final r in releases) {
      final rel = r as Map<String, dynamic>;
      if (rel['draft'] == true || rel['prerelease'] == true) continue;
      final tag = (rel['tag_name'] as String?) ?? '';
      if (!tag.startsWith('mobile-v')) continue; // ignore desktop releases

      final version = _tagToVersion(tag);
      if (!_isNewer(version, current)) return null; // newest mobile <= current

      String? apkUrl;
      for (final a in (rel['assets'] as List? ?? const [])) {
        final asset = a as Map<String, dynamic>;
        final name = (asset['name'] as String? ?? '').toLowerCase();
        if (name.endsWith('.apk')) {
          apkUrl = asset['browser_download_url'] as String?;
          break;
        }
      }
      return UpdateInfo(
        version: version,
        tag: tag,
        apkUrl: apkUrl,
        releaseUrl: (rel['html_url'] as String?) ?? '',
        notes: (rel['body'] as String?) ?? '',
      );
    }
    return null; // no mobile release found
  }

  /// Download the APK to a temp file, reporting progress in 0..1.
  Future<File> downloadApk(
    String apkUrl, {
    void Function(double progress)? onProgress,
  }) async {
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/finance_mobile_update.apk');
    final client = http.Client();
    try {
      final req = http.Request('GET', Uri.parse(apkUrl));
      final resp = await client.send(req);
      if (resp.statusCode != 200) {
        throw HttpException('download ${resp.statusCode}');
      }
      final total = resp.contentLength ?? 0;
      var received = 0;
      final sink = file.openWrite();
      await for (final chunk in resp.stream) {
        sink.add(chunk);
        received += chunk.length;
        if (total > 0 && onProgress != null) {
          onProgress(received / total);
        }
      }
      await sink.close();
      return file;
    } finally {
      client.close();
    }
  }

  /// Strip the tag prefix to a bare version ("mobile-v0.2.0" -> "0.2.0").
  static String _tagToVersion(String tag) {
    var t = tag.trim();
    for (final p in const ['mobile-v', 'desktop-v', 'v']) {
      if (t.startsWith(p)) {
        t = t.substring(p.length);
        break;
      }
    }
    final plus = t.indexOf('+'); // drop build metadata if present
    return plus >= 0 ? t.substring(0, plus) : t;
  }

  /// True when [candidate] is a strictly newer version than [current]
  /// (numeric dot-separated compare; missing parts treated as 0).
  static bool _isNewer(String candidate, String current) {
    final a = _parts(candidate);
    final b = _parts(current);
    final n = a.length > b.length ? a.length : b.length;
    for (var i = 0; i < n; i++) {
      final x = i < a.length ? a[i] : 0;
      final y = i < b.length ? b[i] : 0;
      if (x != y) return x > y;
    }
    return false;
  }

  static List<int> _parts(String v) {
    return v
        .split('.')
        .map((s) => int.tryParse(s.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0)
        .toList();
  }
}
