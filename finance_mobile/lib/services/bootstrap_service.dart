import 'accounts_meta_service.dart';
import 'categories_service.dart';

class BootstrapService {
  final String workspaceId;

  BootstrapService({required this.workspaceId});

  Future<void> ensureWorkspaceMeta() async {
    try {
      await CategoriesService(workspaceId: workspaceId).ensureDoc();
    } catch (_) {}
    try {
      await AccountsMetaService(workspaceId: workspaceId).ensureDoc();
    } catch (_) {}
  }
}


