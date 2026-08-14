import 'package:flutter/foundation.dart';

class SecureLogger {
  // Regex to match typical email addresses
  static final RegExp _emailRegex = RegExp(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
  );
  // Regex to match potential tokens or long alphanumeric secrets
  static final RegExp _tokenRegex = RegExp(r'\b[a-zA-Z0-9_-]{32,}\b');

  static void log(String message) {
    if (kReleaseMode) {
      // In production, we can completely suppress certain logs,
      // or at least heavily redact them.
      // For now, we print nothing or only print critical errors if we had levels.
      return;
    }

    // In debug/profile modes, we print but redact PII and secrets
    final redactedMessage = _redact(message);
    debugPrint(redactedMessage);
  }

  static void error(String message, [Object? error, StackTrace? stackTrace]) {
    final redactedMessage = _redact(message);
    final redactedError = error != null ? _redact(error.toString()) : null;

    debugPrint('ERROR: $redactedMessage');
    if (redactedError != null) {
      debugPrint('Details: $redactedError');
    }
    if (stackTrace != null) {
      debugPrint('Stacktrace:\n$stackTrace');
    }
  }

  static String _redact(String input) {
    String output = input;
    // Redact emails
    output = output.replaceAll(_emailRegex, '[REDACTED_EMAIL]');
    // Redact tokens/secrets
    output = output.replaceAll(_tokenRegex, '[REDACTED_SECRET]');
    return output;
  }
}
