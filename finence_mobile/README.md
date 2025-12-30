### Finence Mobile (Flutter) — MVP

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
From `finence_mobile/`:

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


