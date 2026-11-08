import 'package:flutter_test/flutter_test.dart';
import 'package:finance_mobile/models/category_lists.dart';

void main() {
  final doc = <String, dynamic>{
    'income': ['משכורת'],
    'outcome': ['מזון', 'סופר ומכולת', 'אוכל בחוץ', 'טרם סווג', 'שונות', 'העברה', 'חתולים'],
    'outcome_tree': [
      {'id': 'food', 'name': 'מזון', 'parent_id': ''},
      {'id': 'food.grocery', 'name': 'סופר ומכולת', 'parent_id': 'food'},
      {'id': 'food.restaurants', 'name': 'אוכל בחוץ', 'parent_id': 'food'},
      {'id': 'unclassified', 'name': 'טרם סווג', 'parent_id': ''},
    ],
    'legacy_aliases': {'בתי קפה': 'אוכל בחוץ', 'שונות': 'טרם סווג'},
  };

  test('reads the hierarchy written by the desktop', () {
    final l = CategoryLists.fromDoc(doc);
    expect(l.hasTree, isTrue);
    expect(l.parents.map((n) => n.name), ['מזון', 'טרם סווג']);
    expect(l.childrenOf('מזון').map((n) => n.name), ['סופר ומכולת', 'אוכל בחוץ']);
    expect(l.parentOf('אוכל בחוץ'), 'מזון');
    expect(l.parentOf('מזון'), isNull);
    expect(l.legacyAliases['בתי קפה'], 'אוכל בחוץ');
  });

  test('extra names exclude tree nodes, retired names and transfers', () {
    expect(CategoryLists.fromDoc(doc).extraOutcome, ['חתולים']);
  });

  test('an old document without a hierarchy still works (flat lists)', () {
    final l = CategoryLists.fromDoc({'income': ['משכורת'], 'outcome': ['קניות']});
    expect(l.hasTree, isFalse);
    expect(l.outcome, ['קניות']);
    expect(l.parents, isEmpty);
  });
}
