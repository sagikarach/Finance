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

  /// Secondary actions collapsed into a single trailing "⋮" menu, so the row
  /// doesn't overflow the AppBar when there are many actions.
  final List<HeaderAction> overflow;

  const HeaderActionsRow({
    super.key,
    required this.actions,
    this.title,
    this.overflow = const <HeaderAction>[],
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

    if (overflow.isNotEmpty) {
      items.add(
        PopupMenuButton<int>(
          tooltip: 'עוד',
          icon: const Icon(Icons.more_vert),
          iconSize: 22,
          padding: EdgeInsets.zero,
          onSelected: (i) => overflow[i].onPressed?.call(),
          itemBuilder: (context) => [
            for (var i = 0; i < overflow.length; i++)
              PopupMenuItem<int>(
                value: i,
                enabled: overflow[i].onPressed != null,
                child: Row(
                  children: [
                    Icon(overflow[i].icon, size: 20),
                    const SizedBox(width: 12),
                    Text(overflow[i].tooltip),
                  ],
                ),
              ),
          ],
        ),
      );
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: items,
    );
  }
}


