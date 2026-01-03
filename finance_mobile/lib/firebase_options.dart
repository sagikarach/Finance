import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      throw UnsupportedError('Web FirebaseOptions not configured.');
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      case TargetPlatform.macOS:
        throw UnsupportedError('macOS FirebaseOptions not configured.');
      case TargetPlatform.windows:
        throw UnsupportedError('Windows FirebaseOptions not configured.');
      case TargetPlatform.linux:
        throw UnsupportedError('Linux FirebaseOptions not configured.');
      case TargetPlatform.fuchsia:
        throw UnsupportedError('Fuchsia FirebaseOptions not configured.');
    }
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyBplGiKKuoc1tRYDZkjSXPH-cCgM6ULegg',
    appId: '1:315375720464:android:40e66df68ae845963ed295',
    messagingSenderId: '315375720464',
    projectId: 'finance-app-49ffa',
    storageBucket: 'finance-app-49ffa.firebasestorage.app',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyCaM1AhTW1w6sQAs8sU88gGFaTG0IbnZVo',
    appId: '1:315375720464:ios:ae3020e1914dbe4d3ed295',
    messagingSenderId: '315375720464',
    projectId: 'finance-app-49ffa',
    storageBucket: 'finance-app-49ffa.firebasestorage.app',
    iosBundleId: 'com.example.financeMobile',
  );
}


