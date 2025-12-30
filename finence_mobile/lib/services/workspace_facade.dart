import 'workspace_service.dart';
import 'session_service.dart';

class WorkspaceFacade {
  final WorkspaceService _workspaces;
  final SessionService _session;

  WorkspaceFacade({
    WorkspaceService? workspaces,
    SessionService? session,
  })  : _workspaces = workspaces ?? WorkspaceService(),
        _session = session ?? const SessionService();

  bool get isLoggedIn => _session.isLoggedIn;

  Future<String?> getActiveWorkspaceId() async {
    final uid = _session.requireUid();
    return _workspaces.getActiveWorkspaceId(uid);
  }

  Future<void> joinByCode({
    required String code,
    String role = 'editor',
  }) async {
    final wid = code.trim();
    if (wid.isEmpty) return;
    final uid = _session.requireUid();
    await _workspaces.validateWorkspaceExists(wid);
    await _workspaces.ensureMembership(uid: uid, wid: wid, role: role);
    await _workspaces.setActiveWorkspaceId(uid, wid);
  }

  Future<String> createWorkspace({String? forcedId}) async {
    final uid = _session.requireUid();
    final wid = (forcedId ?? '').trim().isNotEmpty
        ? forcedId!.trim()
        : _workspaces.generateWorkspaceCode();
    await _workspaces.ensureMembership(uid: uid, wid: wid, role: 'owner');
    await _workspaces.setActiveWorkspaceId(uid, wid);
    return wid;
  }

  Future<void> disconnect() async {
    final uid = _session.requireUid();
    await _workspaces.setActiveWorkspaceId(uid, '');
  }

  String generateWorkspaceCode() => _workspaces.generateWorkspaceCode();
}


