import 'dart:developer' as developer;

import 'accounts_meta_service.dart';
import 'categories_service.dart';

class BootstrapService {
  static const String _logName = 'BootstrapService';

  final String workspaceId;

  BootstrapService({required this.workspaceId});

  Future<void> ensureWorkspaceMeta() async {
    try {
      await CategoriesService(workspaceId: workspaceId).ensureDoc();
    } catch (e, st) {
      developer.log(
        'ensureDoc failed for categories (workspaceId=$workspaceId): $e',
        name: _logName,
        error: e,
        stackTrace: st,
      );
    }
    try {
      await AccountsMetaService(workspaceId: workspaceId).ensureDoc();
    } catch (e, st) {
      developer.log(
        'ensureDoc failed for accounts_meta (workspaceId=$workspaceId): $e',
        name: _logName,
        error: e,
        stackTrace: st,
      );
    }
  }
}


