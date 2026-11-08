import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:finance_mobile/models/category_lists.dart';
import 'package:finance_mobile/widgets/category_picker.dart';

void main() {
  final lists = CategoryLists.fromDoc({
    'outcome': ['מזון', 'סופר ומכולת', 'אוכל בחוץ', 'טרם סווג'],
    'outcome_tree': [
      {'id': 'food', 'name': 'מזון', 'parent_id': ''},
      {'id': 'food.grocery', 'name': 'סופר ומכולת', 'parent_id': 'food'},
      {'id': 'food.restaurants', 'name': 'אוכל בחוץ', 'parent_id': 'food'},
      {'id': 'unclassified', 'name': 'טרם סווג', 'parent_id': ''},
    ],
  });

  Future<List<String>> pump(WidgetTester tester, {String selected = 'טרם סווג'}) async {
    final chosen = <String>[];
    await tester.pumpWidget(MaterialApp(
      home: Directionality(
        textDirection: TextDirection.rtl,
        child: Scaffold(
          body: CategoryHierarchyPicker(
            lists: lists,
            extraNames: const ['חתולים'],
            selected: selected,
            accent: Colors.deepOrange,
            onSelected: chosen.add,
            onAddNew: () => chosen.add('<new>'),
          ),
        ),
      ),
    ));
    return chosen;
  }

  testWidgets('subcategories hidden until the arrow is pressed', (tester) async {
    await pump(tester);
    expect(find.text('מזון'), findsOneWidget);
    expect(find.byKey(const ValueKey('expand:מזון')), findsOneWidget); // arrow always there
    expect(find.text('סופר ומכולת'), findsNothing);

    await tester.tap(find.byKey(const ValueKey('expand:מזון')));
    await tester.pump();
    expect(find.text('סופר ומכולת'), findsOneWidget);
    expect(find.text('אוכל בחוץ'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('expand:מזון')));
    await tester.pump();
    expect(find.text('סופר ומכולת'), findsNothing);
  });

  testWidgets('the arrow does not select; names do', (tester) async {
    final chosen = await pump(tester);
    await tester.tap(find.byKey(const ValueKey('expand:מזון')));
    await tester.pump();
    expect(chosen, isEmpty);
    await tester.tap(find.text('אוכל בחוץ'));
    await tester.tap(find.text('מזון'));
    await tester.tap(find.text('חתולים'));
    await tester.tap(find.text('＋ חדש'));
    expect(chosen, ['אוכל בחוץ', 'מזון', 'חתולים', '<new>']);
  });

  testWidgets('categories without subcategories have no arrow', (tester) async {
    await pump(tester);
    expect(find.text('טרם סווג'), findsOneWidget);
    expect(find.byKey(const ValueKey('expand:טרם סווג')), findsNothing);
  });
}
