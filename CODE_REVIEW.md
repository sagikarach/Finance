# Finance — Code Review

**Reviewed:** April 28, 2026
**Scope:** `finance/` (Qt desktop app, ~34.6k LOC Python), `finance_mobile/lib/` (Flutter app, ~5.6k LOC Dart), `scripts/` (~1.3k LOC Python + shell)
**Method:** Static read-through, `ruff` lint sweep, targeted spot-checks. No code was modified.

---

## TL;DR

The codebase is reasonably well-organized — clean separation between models, data providers, pages, dialogs, and widgets on the desktop side; auth-gate / workspace / dashboard layering on mobile. Architecture is sound and the dual-runtime Qt shim (`finance/qt.py`) plus push-only Firebase sync are nice touches.

The two things that need attention right away:

1. **Two latent `NameError` crashes** in the desktop app (update flow and outcome review dialog). These are not theoretical — `ruff` flagged the missing imports and the call sites are reachable from normal user paths.
2. **Firebase API keys committed in source** (`finance_mobile/lib/firebase_options.dart`). Not technically a "secret" by Google's definition, but combined with weak workspace-join validation it widens the blast radius if rules are ever loose.

After that, the dominant theme is **silent error suppression** — `1742` occurrences of `except Exception:` (often with `pass`) in `finance/`. That makes production debugging nearly impossible and hides the kinds of bugs that cause sporadic UI weirdness.

---

## High Priority

### 1. `NameError` — `Qt` not imported in `main_window.py`
**File:** `finance/ui/main_window.py:273, 359`
The update-check and download-update flows call `Qt.WindowModality.WindowModal`, but the `from ..qt import …` statement at line 20 only imports `QAction, QMainWindow, QStackedWidget, QTimer`. As soon as either flow runs, Python raises `NameError: name 'Qt' is not defined`.
**Fix:** Add `Qt` to the import list at `main_window.py:20`.

### 2. `NameError` — `QWidget` not imported in `outcome_review_dialog.py`
**File:** `finance/ui/outcome_review_dialog.py:46`
`info_card = QWidget(self)` is called, but the `from ..qt import …` block (lines 5–12) imports only `QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, Qt`. Opening the outcome-review dialog raises `NameError`.
**Fix:** Add `QWidget` to the import list.

### 3. Plaintext password in user profile
**Files:** `data/user_profile_store.py:54-66`, `user_profile.json`
`user_profile.json` exposes a `"password"` field stored as plaintext (currently `null`, but the schema supports a real value). The codebase already has `finance/models/keychain_passwords.py` for the Gemini key — the same pattern should be reused.
**Fix:** Hash the PIN/password (PBKDF2/scrypt/argon2 with salt) or keep it in macOS Keychain. Never write the cleartext to JSON.

### 4. Firebase API keys committed to the repo
**File:** `finance_mobile/lib/firebase_options.dart:25-40`
Android and iOS `apiKey` values are hard-coded. Google considers Firebase Web/iOS/Android API keys non-secret as long as Firestore/Auth/Storage rules are tight, but:
- A leaked key can still be abused for quota/abuse vectors.
- The mobile `WorkspaceFacade.joinByCode` (`workspace_facade.dart:21–31`) only checks that the workspace exists before joining as `editor` — server-side rules absolutely must enforce membership/role limits.
**Fix:** Confirm Firestore security rules cover everything (per-user `uid` checks, workspace member lists, deletes). Restrict the keys by package name / SHA-1 in the Google Cloud console.

### 5. Daemon thread touching Qt from a worker
**File:** `finance/ui/main_window.py:111`
A `daemon=True` thread runs the Firebase startup-sync worker. The worker calls `QTimer.singleShot(0, self, _ui_refresh)` — that crosses the Qt thread boundary. It usually works because `QTimer.singleShot` with an object owner posts an event to the owner's thread, but no shutdown path joins the worker. If the user closes the window mid-sync, the worker can call into a half-destroyed `MainWindow`.
**Fix:** Track the thread on `self`, signal cancellation on `closeEvent`, and `join` with a small timeout. Better: move the work to a `QThread` and use signals.

### 6. Silent error swallowing in the Flutter bootstrap
**File:** `finance_mobile/lib/services/bootstrap_service.dart:9–15`
Both `ensureDoc()` calls are wrapped in `try { … } catch (_) {}`. If one fails (offline, perms, quota), downstream screens load with empty defaults and the user sees no clue.
**Fix:** Log via `developer.log`, surface a toast/banner, and consider a one-shot retry.

---

## Medium Priority

### 7. `BuildContext` used after `await`
- `finance_mobile/lib/screens/workspace_gate.dart:77` — `ScaffoldMessenger.of(context)` after the `await _workspaces.createWorkspace()` on line 74. There is a `if (!mounted) return;` guard at line 75, so this is *technically* safe, but it relies on the lint-suppression discipline staying clean.
- `finance_mobile/lib/screens/new_movement_screen.dart:225` — same shape inside an async `onTap`.
**Fix:** Capture `final messenger = ScaffoldMessenger.of(context);` before the `await`, then call `messenger.showSnackBar(...)` after.

### 8. `TextEditingController` created in `build()`
**File:** `finance_mobile/lib/screens/workspace_gate.dart:102`
`final codeCtrl = TextEditingController();` lives inside `build()`. Every rebuild allocates a new controller and drops the old one without disposing it.
**Fix:** Move it to `initState`, store on `State`, dispose in `dispose()`.

### 9. `1742` broad `except Exception:` blocks in `finance/`
**Files:** all over (`csv_expense_parser.py:91-95`, `firebase_client.py:68-88`, dozens of widgets/pages).
Most do `except Exception: pass` or `except Exception: return None`. This pattern is the single biggest debugging hazard in the codebase.
**Fix:** At minimum, route them through a small helper that calls `logging.exception(...)` so failures are recoverable from a log. Re-raise where the failure is meaningful.

### 10. Concurrent sync race in `DashboardScreen`
**File:** `finance_mobile/lib/screens/dashboard_screen.dart:91, 421-443`
`_pullFromServer()` has no in-flight guard, and `_openAddMovement()` only blocks itself. Two near-simultaneous syncs can interleave on shared state (`_movements`, `_actions`, `_movementDetailsById`) and produce flickers / stale UI.
**Fix:** Add a `bool _syncing` field; bail early if already syncing. Same pattern works for `_ensureMovementBackfill`.

### 11. ML training file written without locking
**File:** `finance/models/movement_classifier.py:96-104, 303-324`
`set_training_data()` and `learn()` write `expenses.json` non-atomically. A concurrent classifier learn during a sync can corrupt the file.
**Fix:** Write to a temp file in the same directory and `os.replace` it. Wrap with a `threading.Lock` if learn can run from multiple threads.

### 12. `_GLOBAL_SYNCING` and `_classifier` singletons aren't thread-safe
**Files:** `finance/pages/base_page.py` (search `_GLOBAL_SYNCING`), `finance/models/gemini_classifier.py:443-451`
Module-level mutable state read/written from background threads without a lock. Mostly harmless because Python's GIL makes single-attribute reads/writes atomic, but the double-check init in `get_gemini_classifier()` can construct two instances under contention.
**Fix:** Wrap with a `threading.Lock` (or `functools.lru_cache(maxsize=None)` for the singleton).

### 13. Build / release scripts
- `scripts/restore_savings_from_backup.py:46` hard-codes `BACKUP_PATH` and `TARGET_WORKSPACE`. Move to env vars / CLI args.
- `scripts/import_legacy_savings.py:334-340` runs in `replace` mode without an explicit confirmation flag — destructive operation.
- `scripts/build_macos_app.sh:21` runs `codesign` without checking the exit code.
- `scripts/check_yaml.sh:8,10-28` doesn't validate `PYTHON_BIN` before use.

### 14. Linter findings worth cleaning up
`ruff` reports 35 issues; 20 auto-fixable. Most are unused imports (`F401`), but a couple are not:
- `finance/widgets/savings_history_chart.py:310-319` — multiple statements on one line (E702) — slip-ups likely from a refactor.
- `scripts/restore_savings_from_backup.py:36-40` — `E402` imports after code; means a `sys.path` hack that should be refactored.
- `scripts/generate_release_keys.py:50-53` — `f""` strings with no placeholders (probably a copy-paste).

Run `python3 -m ruff check finance/ main.py scripts/ --fix` to clear the easy ones, then handle the F821 / E702 / E402 by hand.

---

## Low Priority

15. Inconsistent confidence thresholds: similarity classifier caps at 0.7 (`movement_classifier.py:173`), Gemini at 0.85 (`gemini_classifier.py:20`). Document the intent or harmonize.
16. `csv_expense_parser.py:15-30` has two near-duplicate cleaners (`clean_description`, `_normalize`); consolidate.
17. `firebase_client.py:244-269` — `list_user_movements()` accumulates all pages in memory. Fine for typical use, but expose a generator variant for backups.
18. Hebrew-only error messages — fine for the target audience but worth noting if the app ever opens up to other locales.
19. `LaunchTargetService._targets` (`launch_target_service.dart:11`) is a singleton broadcast `StreamController` that's never closed. Practically harmless because it lives for the app lifetime, but worth a `close()` for hot-reload hygiene.
20. Duplicated typo handling for `asign_movment_to_one_time_event` vs `assign_movment_to_one_time_event` in `dashboard_screen.dart:163` — fine as defensive code, but the underlying backend data should be cleaned up.

---

## Notes

- Type hint coverage on the desktop side is pretty good — most public methods have annotations. Pyright is configured (`pyrightconfig.json`) but `mypy` cache is also present, suggesting both have been run at various points. Pick one as the canonical type checker.
- The Qt compatibility layer (`finance/qt.py`) is well-done — single source of truth for PySide6 ↔ PyQt6.
- Push-only Firebase sync architecture is sensible. The `sync_gate` pattern (only push when conditions are right) is a nice safeguard against accidental writes.
- Tests directory is absent. None of the 110+ Python files in `finance/` ships with unit tests, and the Flutter side has no `test/` folder either. For a financial app, that's the gap I'd close next after the bug fixes above.

---

## Suggested Order of Operations

1. Fix the two `NameError`s (#1, #2) — single-line edits, prevents real crashes.
2. Hash/keychain the user password (#3).
3. Lock down Firebase rules and restrict the API keys (#4).
4. Add a `_syncing` guard on the dashboard pull (#10) and dispose `codeCtrl` properly (#8).
5. Replace `except Exception: pass` with a logging helper (#9) — incremental, file by file.
6. Run `ruff --fix` and clean the residual issues (#14).
7. Start adding tests around `csv_expense_parser`, `movement_classifier`, and the Firebase sync state machine.
