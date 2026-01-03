import 'package:cloud_firestore/cloud_firestore.dart';

import '../models/category_lists.dart';

class CategoriesService {
  final String workspaceId;

  CategoriesService({required this.workspaceId});

  DocumentReference<Map<String, dynamic>> _doc() {
    return FirebaseFirestore.instance
        .collection('workspaces')
        .doc(workspaceId)
        .collection('meta')
        .doc('categories');
  }

  Future<void> ensureDoc() async {
    final ref = _doc();
    final snap = await ref.get();
    if (snap.exists) return;

    await ref.set(<String, Object?>{
      'income': <String>[],
      'outcome': <String>[],
      'updated_at': FieldValue.serverTimestamp(),
      'version': 1,
    });
  }

  Future<CategoryLists> fetch({Source source = Source.server}) async {
    final snap = await _doc().get(GetOptions(source: source));
    return CategoryLists.fromDoc(snap.data());
  }

  Future<void> addCategory({
    required bool isIncome,
    required String name,
  }) async {
    final n = name.trim();
    if (n.isEmpty) return;
    await _doc().set(<String, Object?>{
      isIncome ? 'income' : 'outcome': FieldValue.arrayUnion(<String>[n]),
      'updated_at': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }
}


