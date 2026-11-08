/// A node of the expense-category hierarchy (written by the desktop app into
/// `meta/categories.outcome_tree`). Parent/child links use stable ids.
class CategoryNode {
  final String id;
  final String name;
  final String? parentId;

  const CategoryNode({required this.id, required this.name, this.parentId});
}

class CategoryLists {
  /// Shown when nothing better is known (matches the desktop).
  static const unclassified = 'טרם סווג';

  final List<String> income;
  final List<String> outcome;

  /// Expense hierarchy; empty for a budget the desktop has not migrated.
  final List<CategoryNode> tree;

  /// Retired category name → its replacement. Retired names are not offered.
  final Map<String, String> legacyAliases;

  const CategoryLists({
    required this.income,
    required this.outcome,
    this.tree = const [],
    this.legacyAliases = const {},
  });

  static CategoryLists fromDoc(Map<String, dynamic>? data) {
    List<String> names(Object? raw) => ((raw as List?) ?? const [])
        .map((e) => e.toString())
        .where((s) => s.trim().isNotEmpty)
        .toList();

    final tree = <CategoryNode>[];
    final rawTree = data?['outcome_tree'];
    if (rawTree is List) {
      for (final item in rawTree) {
        if (item is! Map) continue;
        final id = (item['id'] ?? '').toString().trim();
        final name = (item['name'] ?? '').toString().trim();
        final parent = (item['parent_id'] ?? '').toString().trim();
        if (id.isEmpty || name.isEmpty) continue;
        tree.add(CategoryNode(id: id, name: name, parentId: parent.isEmpty ? null : parent));
      }
    }
    final aliases = <String, String>{};
    final rawAliases = data?['legacy_aliases'];
    if (rawAliases is Map) {
      rawAliases.forEach((k, v) {
        final key = k.toString().trim();
        final value = (v ?? '').toString().trim();
        if (key.isNotEmpty && value.isNotEmpty) aliases[key] = value;
      });
    }
    return CategoryLists(
      income: names(data?['income']),
      outcome: names(data?['outcome']),
      tree: tree,
      legacyAliases: aliases,
    );
  }

  bool get hasTree => tree.isNotEmpty;

  CategoryNode? byName(String name) {
    for (final n in tree) {
      if (n.name == name) return n;
    }
    return null;
  }

  /// Top-level expense categories, in hierarchy order.
  List<CategoryNode> get parents => tree.where((n) => n.parentId == null).toList();

  List<CategoryNode> childrenOf(String parentName) {
    final p = byName(parentName);
    if (p == null) return const [];
    return tree.where((n) => n.parentId == p.id).toList();
  }

  /// The parent's name for a subcategory, else null.
  String? parentOf(String name) {
    final n = byName(name);
    if (n == null || n.parentId == null) return null;
    for (final p in tree) {
      if (p.id == n.parentId) return p.name;
    }
    return null;
  }

  /// Expense names offered outside the hierarchy (custom names added on any
  /// device), excluding retired names and transfers.
  List<String> get extraOutcome => outcome
      .where((n) =>
          byName(n) == null && !legacyAliases.containsKey(n) && n.trim() != 'העברה')
      .toList();
}
