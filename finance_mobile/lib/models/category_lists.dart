class CategoryLists {
  final List<String> income;
  final List<String> outcome;

  const CategoryLists({
    required this.income,
    required this.outcome,
  });

  static CategoryLists fromDoc(Map<String, dynamic>? data) {
    final incomeRaw = (data?['income'] as List?) ?? const [];
    final outcomeRaw = (data?['outcome'] as List?) ?? const [];
    return CategoryLists(
      income: incomeRaw.map((e) => e.toString()).where((s) => s.trim().isNotEmpty).toList(),
      outcome: outcomeRaw.map((e) => e.toString()).where((s) => s.trim().isNotEmpty).toList(),
    );
  }
}


