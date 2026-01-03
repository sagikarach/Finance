import 'package:firebase_auth/firebase_auth.dart';

class SessionService {
  const SessionService();

  User? get currentUser => FirebaseAuth.instance.currentUser;

  String? get uid => currentUser?.uid;

  bool get isLoggedIn => currentUser != null;

  String requireUid() {
    final u = uid;
    if (u == null || u.trim().isEmpty) {
      throw StateError('Not logged in');
    }
    return u;
  }

  Future<void> signOut() => FirebaseAuth.instance.signOut();
}


