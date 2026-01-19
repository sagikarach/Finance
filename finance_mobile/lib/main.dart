import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'firebase_options.dart';
import 'screens/login_screen.dart';
import 'screens/workspace_gate.dart';
import 'services/launch_target_service.dart';
import 'theme/app_theme.dart';
import 'widgets/app_lock_gate.dart';

Future<void> _initAppServices() async {
  try {
    await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  } catch (_) {
    await Firebase.initializeApp();
  }
  await LaunchTargetService.instance.init();
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const FinanceMobileApp());
}

class FinanceMobileApp extends StatelessWidget {
  const FinanceMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Finance',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      locale: const Locale('he'),
      supportedLocales: const [Locale('he')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, child) => Directionality(
        textDirection: TextDirection.rtl,
        child: child ?? const SizedBox.shrink(),
      ),
      home: const _RootGate(),
    );
  }
}

class _RootGate extends StatefulWidget {
  const _RootGate();

  @override
  State<_RootGate> createState() => _RootGateState();
}

class _RootGateState extends State<_RootGate> {
  late Future<void> _initFuture;

  @override
  void initState() {
    super.initState();
    _initFuture = _initAppServices();
  }

  void _retry() {
    setState(() {
      _initFuture = _initAppServices();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<void>(
      future: _initFuture,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        if (snap.hasError) {
          return Scaffold(
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'שגיאה באתחול Firebase',
                      style: TextStyle(fontWeight: FontWeight.w800),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      '${snap.error}',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    ElevatedButton(
                      onPressed: _retry,
                      child: const Text('נסה שוב'),
                    ),
                  ],
                ),
              ),
            ),
          );
        }

        return StreamBuilder<User?>(
        stream: FirebaseAuth.instance.authStateChanges(),
        builder: (context, snapshot) {
          final user = snapshot.data;
          if (user == null) return const LoginScreen();
            // Key by uid so switching accounts resets WorkspaceGate state (no stale workspace/data).
            return AppLockGate(
              child: WorkspaceGate(key: ValueKey(user.uid)),
            );
        },
        );
      },
    );
  }
}
