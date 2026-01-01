import 'package:flutter/material.dart';

class HeaderAction {
  final IconData icon;
  final String tooltip;
  final VoidCallback? onPressed;

  const HeaderAction({
    required this.icon,
    required this.tooltip,
    required this.onPressed,
  });
}

class HeaderActionsRow extends StatelessWidget {
  final String? title;
  final List<HeaderAction> actions;

  const HeaderActionsRow({
    super.key,
    required this.actions,
    this.title,
  });

  @override
  Widget build(BuildContext context) {
    final items = <Widget>[];
    final t = (title ?? '').trim();
    if (t.isNotEmpty) {
      items.add(
        Text(
          t,
          textAlign: TextAlign.center,
          style: const TextStyle(fontWeight: FontWeight.w800),
          overflow: TextOverflow.ellipsis,
        ),
      );
    }

    for (final a in actions) {
      items.add(
        IconButton(
          tooltip: a.tooltip,
          onPressed: a.onPressed,
          icon: Icon(a.icon),
          iconSize: 22,
          padding: EdgeInsets.zero,
          constraints: const BoxConstraints.tightFor(width: 44, height: 44),
        ),
      );
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: items,
    );
  }
}


