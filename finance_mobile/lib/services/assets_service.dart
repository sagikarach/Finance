import 'dart:math' as math;

import 'package:cloud_firestore/cloud_firestore.dart';

/// Current prime interest rate (%), mirrors the desktop `DEFAULT_PRIME_RATE`
/// in finance/models/mortgage_math.py. Used only to estimate prime-track
/// payments — the desktop remains the source of truth for the real schedule.
const double kDefaultPrimeRate = 6.0;

double _numOf(Map<String, dynamic> d, String k) =>
    (d[k] is num) ? (d[k] as num).toDouble() : 0.0;
int _intOf(Map<String, dynamic> d, String k) =>
    (d[k] is num) ? (d[k] as num).toInt() : 0;
String _strOf(Map<String, dynamic> d, String k) => (d[k] as String?) ?? '';
bool _boolOf(Map<String, dynamic> d, String k) => (d[k] as bool?) ?? false;

Map<String, dynamic> _asMap(dynamic v) =>
    (v is Map) ? v.map((k, val) => MapEntry('$k', val)) : <String, dynamic>{};

/// One mortgage track (מסלול) — a row of the mix (תמהיל).
/// Field names mirror the desktop serializer (mortgage_provider.py:69-81).
class MortgageTrack {
  final String id;
  final String name;
  final String kind; // פריים / קבועה צמודה / משתנה לא צמודה ...
  final double principal;
  final double annualRate; // % (ignored for prime tracks)
  final int termMonths;
  final String amortization; // שפיצר / קרן שווה
  final bool cpiLinked;
  final double primeSpread; // prime + spread for prime tracks
  final int resetMonths;

  MortgageTrack({
    required this.id,
    required this.name,
    required this.kind,
    required this.principal,
    required this.annualRate,
    required this.termMonths,
    required this.amortization,
    required this.cpiLinked,
    required this.primeSpread,
    required this.resetMonths,
  });

  static MortgageTrack fromMap(Map<String, dynamic> d) => MortgageTrack(
        id: _strOf(d, 'id'),
        name: _strOf(d, 'name'),
        kind: _strOf(d, 'kind'),
        principal: _numOf(d, 'principal'),
        annualRate: _numOf(d, 'annual_rate'),
        termMonths: _intOf(d, 'term_months'),
        amortization: _strOf(d, 'amortization'),
        cpiLinked: _boolOf(d, 'cpi_linked'),
        primeSpread: _numOf(d, 'prime_spread'),
        resetMonths: _intOf(d, 'reset_months'),
      );

  bool get isPrime => kind == 'פריים';

  /// Effective annual rate (%): prime tracks add their spread to the prime
  /// rate; everything else uses its own nominal rate.
  double get effectiveAnnualRate =>
      isPrime ? (kDefaultPrimeRate + primeSpread) : annualRate;

  /// Initial monthly payment estimate. Spitzer (annuity) is (near-)constant;
  /// equal-principal (קרן שווה) starts highest, so we show the first payment.
  /// CPI growth is intentionally ignored — this is the base, as-of-today figure.
  double get monthlyPayment {
    final n = termMonths;
    final p = principal;
    if (n <= 0 || p <= 0) return 0.0;
    final r = effectiveAnnualRate / 100.0 / 12.0;
    final isEqualPrincipal = amortization == 'קרן שווה';
    if (isEqualPrincipal) {
      return p / n + p * r; // first (largest) payment
    }
    if (r == 0.0) return p / n;
    return p * r / (1.0 - math.pow(1.0 + r, -n).toDouble());
  }
}

/// An asset. Houses (`kind == "רכישה"`, or missing) carry a mortgage as their
/// `tracks`; other holdings (`kind == "אחר"`) are just a value.
/// Mirrors the desktop asset/mortgage doc (firebase_workspace_writer.py:226).
class Asset {
  final String id;
  final String name;
  final String kind; // נדל״ן (house) / רכב (car) / אחר (other)
  final double currentValue; // for car / other
  final double propertyPrice; // for house = value; for car = purchase price
  final List<MortgageTrack> tracks;
  final String startDate;
  final bool archived;
  final bool sold;
  final double salePrice;
  final String expenseCategory; // movement category for the car's avg expense

  Asset({
    required this.id,
    required this.name,
    required this.kind,
    required this.currentValue,
    required this.propertyPrice,
    required this.tracks,
    required this.startDate,
    required this.archived,
    required this.sold,
    required this.salePrice,
    required this.expenseCategory,
  });

  /// Kinds mirror the desktop `AssetKind`: נדל״ן (real estate; legacy "רכישה"
  /// or a missing kind also count as this), רכב (car), אחר (other holding).
  bool get isOther => kind == 'אחר';
  bool get isCar => kind == 'רכב';
  bool get isHouse => !isOther && !isCar;

  /// Real estate is worth its property price; a car / other holding is worth
  /// its manually-maintained current value.
  double get value => isHouse ? propertyPrice : currentValue;
  bool get isActive => !archived && !sold;
  bool get hasMortgage => tracks.isNotEmpty;

  // ── car depreciation: purchase price (property_price) vs current value ──
  double get purchasePrice => propertyPrice;
  bool get hasDepreciation => isCar && purchasePrice > 0;
  double get valueLost =>
      hasDepreciation ? (purchasePrice - currentValue).clamp(0.0, purchasePrice) : 0.0;
  double get retainedFraction => (isCar && purchasePrice > 0)
      ? (currentValue / purchasePrice).clamp(0.0, 1.0)
      : 1.0;

  /// Movement category driving the car's average expense (default "רכב").
  String get category {
    final c = expenseCategory.trim();
    return c.isNotEmpty ? c : 'רכב';
  }
  double get mortgagePrincipal =>
      tracks.fold(0.0, (acc, t) => acc + t.principal);
  double get monthlyPayment =>
      tracks.fold(0.0, (acc, t) => acc + t.monthlyPayment);

  /// Rough equity: property value minus the original mortgage principal.
  /// (An estimate — it doesn't amortize the outstanding balance.)
  double get equity => value - mortgagePrincipal;

  static Asset fromFirestore(Map<String, dynamic> d) {
    final rawTracks = d['tracks'];
    final tracks = <MortgageTrack>[];
    if (rawTracks is List) {
      for (final t in rawTracks) {
        if (t is Map) tracks.add(MortgageTrack.fromMap(_asMap(t)));
      }
    }
    return Asset(
      id: _strOf(d, 'id'),
      name: _strOf(d, 'name'),
      kind: _strOf(d, 'kind'),
      currentValue: _numOf(d, 'current_value'),
      propertyPrice: _numOf(d, 'property_price'),
      tracks: tracks,
      startDate: _strOf(d, 'start_date'),
      archived: _boolOf(d, 'archived'),
      sold: _boolOf(d, 'sold'),
      salePrice: _numOf(d, 'sale_price'),
      expenseCategory: _strOf(d, 'expense_category'),
    );
  }
}

/// Reads assets (and their embedded mortgages) from
/// `workspaces/{workspaceId}/mortgages`. The desktop stores each asset as one
/// doc; a house's mortgage is the `tracks` array on that same doc.
class AssetsService {
  final String workspaceId;

  AssetsService({required this.workspaceId});

  CollectionReference<Map<String, dynamic>> _ref() => FirebaseFirestore.instance
      .collection('workspaces')
      .doc(workspaceId)
      .collection('mortgages');

  Future<List<Asset>> fetch({Source source = Source.server}) async {
    final snap = await _ref().get(GetOptions(source: source));
    final out = <Asset>[];
    for (final doc in snap.docs) {
      final data = doc.data();
      if ((data['deleted'] as bool?) ?? false) continue; // tombstone
      final withId = <String, dynamic>{...data};
      if ((withId['id'] as String?)?.isEmpty ?? true) withId['id'] = doc.id;
      out.add(Asset.fromFirestore(withId));
    }
    // Houses first, then by value (largest first).
    out.sort((a, b) {
      if (a.isHouse != b.isHouse) return a.isHouse ? -1 : 1;
      return b.value.compareTo(a.value);
    });
    return out;
  }

  /// Net worth of the active assets: sum of value minus mortgage principal
  /// (the non-liquid wealth folded into the home balance). Mirrors the desktop
  /// `MortgageService.total_assets_net`.
  static double netWorth(List<Asset> assets) => assets
      .where((a) => a.isActive)
      .fold(0.0, (acc, a) => acc + a.value - a.mortgagePrincipal);
}
