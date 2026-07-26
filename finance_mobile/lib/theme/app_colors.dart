import 'package:flutter/material.dart';

/// The soft-pastel palette for the redesigned app. Semantic money colors
/// (green = income, red/clay = expense) are kept distinct from the accents.
class AppColors {
  static const screen = Color(0xFFF4F2EC); // warm off-white page ground
  static const card = Color(0xFFFFFFFF);
  static const ink = Color(0xFF1E1E22); // near-black text / nav
  static const muted = Color(0xFF8B8E86);
  static const line = Color(0xFFECEAE2);

  static const yellow = Color(0xFFF2D06B);
  static const yellowSoft = Color(0xFFF7E2A6);
  static const lav = Color(0xFFB9B6F0);
  static const lavSoft = Color(0xFFDEDDF8);
  static const sage = Color(0xFFC6D3B4);
  static const sageSoft = Color(0xFFDCE7CC);

  static const green = Color(0xFF2F9E68); // income / positive
  static const greenSoft = Color(0xFF8FBF9F);
  static const clay = Color(0xFFD66A4E); // expense / negative
  static const claySoft = Color(0xFFE9A491);

  /// Categorical palette for donut charts, ordered for good contrast.
  static const List<Color> categorical = [
    lav,
    sage,
    yellow,
    claySoft,
    Color(0xFF9BB4E6),
    Color(0xFFD9DCE0),
    greenSoft,
    yellowSoft,
  ];
}
