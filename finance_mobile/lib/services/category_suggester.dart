import '../models/movement.dart';
import '../models/movement_type.dart';

/// A suggested (category, type) for a manually entered movement.
class CategorySuggestion {
  final String category;
  final String type; // MovementType canon
  final double confidence;

  const CategorySuggestion(this.category, this.type, this.confidence);
}

/// Suggests a category (and type) for a new movement from the user's own past
/// movements — a port of the desktop's local similarity classifier, so both
/// apps suggest the same thing. Runs fully on the device: no network, no AI.
///
/// * Only movements of the same direction teach it (expenses for an expense,
///   income for an income); transfers never do. Expenses labelled
///   "טרם סווג"/"שונות"/"אחר" are not examples of anything.
/// * The same description always outranks a partial match; the amount only
///   breaks ties. Its type is the one that description had most often.
/// * Below [minConfidence] it suggests nothing (the desktop uses 0.5).
class CategorySuggester {
  static const double minConfidence = 0.5;
  static const int _maxSimilar = 5;
  static const double _threshold = 0.3;
  static const _noiseWords = {
    'בעמ', 'בע"מ', 'בע׳מ', 'בע״מ', 'בע?מ', 'חברה', 'ישראלי', 'ישראל', 'תשלום',
    'תשלומים', 'דמי', 'כרטיס', 'ויזה', 'לאומי', 'בנק', 'העברה', 'העברות',
    'מפעולות', 'ישיר',
  };
  static const _notALabel = {'טרם סווג', 'שונות', 'אחר', 'אחרים'};

  final List<_Example> _examples;
  final Set<String> _allowed;

  CategorySuggester._(this._examples, this._allowed);

  factory CategorySuggester.fromMovements(
    Iterable<Movement> movements, {
    required bool isIncome,
    required Iterable<String> allowedCategories,
  }) {
    final allowed = allowedCategories.toSet();
    final examples = <_Example>[];
    for (final m in movements) {
      if (m.deleted || m.isTransfer) continue;
      if (isIncome ? m.amount <= 0 : m.amount >= 0) continue;
      final desc = (m.description ?? '').trim();
      final cat = m.category.trim();
      if (desc.isEmpty || cat.isEmpty) continue;
      if (!isIncome && _notALabel.contains(cat)) continue;
      if (allowed.isNotEmpty && !allowed.contains(cat)) continue;
      examples.add(_Example(desc, m.amount.abs(), cat, MovementType.normalize(m.type)));
    }
    return CategorySuggester._(examples, allowed);
  }

  bool get isEmpty => _examples.isEmpty;

  CategorySuggestion? suggest(String description, double amount) {
    final desc = description.trim();
    if (desc.isEmpty || _examples.isEmpty) return null;
    final own = normalize(desc);
    final scored = <_Scored>[];
    for (final e in _examples) {
      final sim = _similarity(desc, amount.abs(), e);
      if (sim > _threshold) scored.add(_Scored(e, sim, own.isNotEmpty && own == normalize(e.description)));
    }
    if (scored.isEmpty) return null;
    scored.sort((a, b) {
      if (a.exact != b.exact) return a.exact ? -1 : 1;
      return b.similarity.compareTo(a.similarity);
    });
    final top = scored.take(_maxSimilar).toList();
    final topSim = top.first.similarity;
    final isExact = topSim > 0.9;

    final String category;
    final String type;
    if (isExact) {
      category = top.first.example.category;
      type = _majorityExactType(scored) ?? top.first.example.type;
    } else {
      category = _weightedPick(top, (s) => s.example.category);
      type = _weightedPick(top, (s) => s.example.type);
    }
    final agreement = top.where((s) => s.example.category == category).length / top.length;
    double confidence;
    if (isExact) {
      confidence = agreement >= 0.6 ? 0.6 + 0.1 * agreement : 0.5 + 0.1 * agreement;
    } else {
      confidence = topSim * (0.4 + 0.4 * agreement);
    }
    if (top.length >= 3) {
      confidence = (confidence * 1.1).clamp(0.0, 0.7);
    } else if (top.length == 1) {
      confidence *= 0.75;
    }
    confidence = confidence.clamp(0.0, 0.7);

    if (confidence < minConfidence) return null;
    if (_allowed.isNotEmpty && !_allowed.contains(category)) return null;
    if (_notALabel.contains(category)) return null;
    return CategorySuggestion(category, type, confidence);
  }

  // ── matching (same rules as the desktop) ──

  static String normalize(String s) {
    final lower = s.toLowerCase();
    final cleaned = lower.replaceAll(RegExp(r'[^0-9a-zא-ת]+'), ' ');
    return cleaned.replaceAll(RegExp(r'\s+'), ' ').trim();
  }

  static Set<String> _tokens(String s) {
    final out = <String>{};
    for (final w in normalize(s).split(' ')) {
      if (w.length <= 1) continue;
      if (RegExp(r'^\d+$').hasMatch(w)) continue;
      if (_noiseWords.contains(w)) continue;
      out.add(w);
    }
    return out;
  }

  static double _overlap(String a, String b) {
    final t1 = _tokens(a);
    final t2 = _tokens(b);
    if (t1.isEmpty || t2.isEmpty) return 0;
    final inter = t1.intersection(t2).length;
    final union = t1.union(t2).length;
    return union == 0 ? 0 : inter / union;
  }

  static double _similarity(String desc, double amount, _Example e) {
    final n1 = normalize(desc);
    final n2 = normalize(e.description);
    double descScore = 0;
    if (n1.isNotEmpty && n2.isNotEmpty && n1 == n2) {
      descScore = 0.6;
    } else if (n1.isNotEmpty && n2.isNotEmpty && (n1.contains(n2) || n2.contains(n1))) {
      descScore = 0.4;
    } else {
      final o = _overlap(desc, e.description);
      if (o >= 0.5) {
        descScore = 0.6;
      } else if (o >= 0.25) {
        descScore = 0.4;
      } else if (o >= 0.12) {
        descScore = 0.3;
      }
    }
    if (descScore <= 0) return 0;
    final diff = (amount - e.amount).abs();
    double amountScore = 0;
    if (diff < 10) {
      amountScore = 0.4;
    } else if (diff < 50) {
      amountScore = 0.3;
    } else if (diff < 100) {
      amountScore = 0.2;
    }
    return descScore + amountScore * (descScore / 0.6);
  }

  /// The type most past movements with this exact description had (seen as
  /// monthly 5 times and one-time once → monthly); a tie goes to the
  /// best-ranked one. Null without an exact match. [ranked] is sorted with
  /// exact matches first.
  static String? _majorityExactType(List<_Scored> ranked) {
    final counts = <String, int>{};
    for (final s in ranked) {
      if (!s.exact) break;
      final t = s.example.type;
      if (t.isEmpty) continue;
      counts[t] = (counts[t] ?? 0) + 1;
    }
    if (counts.isEmpty) return null;
    String best = counts.keys.first;
    counts.forEach((t, n) {
      if (n > counts[best]!) best = t;
    });
    return best;
  }

  static String _weightedPick(List<_Scored> rows, String Function(_Scored) field) {
    final scores = <String, double>{};
    for (final r in rows) {
      final v = field(r);
      if (v.isEmpty) continue;
      scores[v] = (scores[v] ?? 0) + r.similarity;
    }
    if (scores.isEmpty) return '';
    return scores.entries.reduce((a, b) => b.value > a.value ? b : a).key;
  }
}

class _Example {
  final String description;
  final double amount;
  final String category;
  final String type;

  const _Example(this.description, this.amount, this.category, this.type);
}

class _Scored {
  final _Example example;
  final double similarity;
  final bool exact;

  const _Scored(this.example, this.similarity, this.exact);
}
