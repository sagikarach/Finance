### Finance Mobile (Flutter) — MVP

This mobile app lets a user:
- Sign in / register with **Firebase Auth (email/password)**
- Add movements manually
- Save movements to **Firestore** under `users/{uid}/movements/{movementId}`
- See a list of movements (live updates, offline cache supported by Firestore SDK)

### Firebase setup
1. In Firebase Console:
   - Enable **Authentication → Email/Password**
   - Create **Firestore Database**
   - Rules (recommended):

```rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{uid}/{document=**} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
    }
  }
}
```

### Configure the app (FlutterFire)
From `finance_mobile/`:

```bash
flutter pub get
dart pub global activate flutterfire_cli
flutterfire configure
```

This generates `lib/firebase_options.dart` (replace the placeholder).

### Run on Android (USB)
```bash
flutter devices
flutter run
```

If your machine has multiple Java versions installed, Android builds typically require **Java 17**.
You can run:

```bash
./scripts/run_android.sh
```

### Build APK (send to your phone)
```bash
flutter build apk --release
```

APK location:
- `build/app/outputs/flutter-apk/app-release.apk`

### Data format (must match desktop sync)
Movement document fields:
- `id` (uuid)
- `amount` (+income, -expense)
- `date` (YYYY-MM-DD)
- `account_name` (free text)
- `category` (free text)
- `type` (MONTHLY | YEARLY | ONE_TIME)
- `description` (optional)
- `event_id` (optional)
- `deleted` (bool)

#### Asset document (`workspaces/{workspaceId}/mortgages/{mortgageId}`)
The collection is named `mortgages` (historical) but each doc is an **asset**.
Desktop-only today; documented so a future mobile asset view stays consistent.
Reconciliation **already works with mobile-created movements** — it matches by
`description` (and `account_name` where relevant), so no mobile code is required.

Top-level fields:
- `id` (uuid)
- `name` (free text)
- `kind` (רכישה = purchase asset | אחר = other holding)
- `current_value` (number — for `kind = אחר` only)
- `account_name` (source account for the loan payments; fixed to "בנק")
- `vendor_query` (text matched against movement `description` for loan payments)
- `start_date` (YYYY-MM-DD)
- `excluded_movement_ids` (array of movement ids excluded from matching)
- `archived` (bool) · `deleted` (bool)

Purchase fields (`kind = רכישה`):
- `property_price` (number — the house price; appears as a payment/money-out)
- `price_query` (text matched against the payment(s) to the seller; transfers included)
- `tracks` (array of maps — the תמהיל / mortgage; its sum **is** the mortgage), each:
  - `id`, `name`
  - `kind` (פריים | קבועה לא צמודה | קבועה צמודה | משתנה לא צמודה | משתנה צמודה)
  - `principal` (number) · `annual_rate` (number, % — ignored for prime)
  - `term_months` (int) · `amortization` (שפיצר | קרן שווה)
  - `cpi_linked` (bool) · `prime_spread` (number, prime: rate = prime + spread)
  - `reset_months` (int — variable reset period, 0 = none)
- `one_time_costs` / `monthly_costs` (arrays of maps), each: `name`, `amount`,
  `query` (optional text → "paid in practice" from matched movements)
- `funding_sources` (array of maps — the income side), each: `name`, `amount`,
  `kind` (חשבון קיים | תנועות | עתידי), `query` (for תנועות),
  `account_name` + `saving_name` (for חשבון קיים — a bank account or a specific
  sub-saving). The mortgage covers the rest; the "בנק" account covers any
  residual (`property_price + costs − mortgage − funding`), shown negative if short.


