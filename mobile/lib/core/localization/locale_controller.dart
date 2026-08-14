import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../database/database_helper.dart';

abstract interface class LocalePreferenceStore {
  Future<String?> read();

  Future<void> write(String languageCode);
}

final class SqliteLocalePreferenceStore implements LocalePreferenceStore {
  SqliteLocalePreferenceStore({Future<Database>? database})
    : _databaseOverride = database;

  final Future<Database>? _databaseOverride;

  Future<Database> get _database =>
      _databaseOverride ?? DatabaseHelper.instance.database;

  @override
  Future<String?> read() async {
    final db = await _database;
    final rows = await db.query(
      'application_state',
      columns: ['locale'],
      where: 'singleton_id = 1',
      limit: 1,
    );
    if (rows.length != 1) {
      throw StateError('APPLICATION_STATE_SINGLETON_MISSING');
    }
    return rows.single['locale'] as String?;
  }

  @override
  Future<void> write(String languageCode) async {
    final db = await _database;
    final affected = await db.update('application_state', {
      'locale': languageCode,
    }, where: 'singleton_id = 1');
    if (affected != 1) {
      throw StateError('APPLICATION_STATE_SINGLETON_MISSING');
    }
  }
}

final class LocaleController extends ChangeNotifier {
  LocaleController({LocalePreferenceStore? store, Locale? initialLocale})
    : _store = store ?? SqliteLocalePreferenceStore(),
      _locale = initialLocale ?? const Locale('ar');

  static const supportedLanguageCodes = {'ar', 'en'};

  final LocalePreferenceStore _store;
  Locale _locale;

  Locale get locale => _locale;

  Future<void> load() async {
    final languageCode = await _store.read();
    if (languageCode == null) return;
    _validate(languageCode);
    final loaded = Locale(languageCode);
    if (loaded == _locale) return;
    _locale = loaded;
    notifyListeners();
  }

  Future<void> setLocale(Locale locale) async {
    _validate(locale.languageCode);
    if (_locale.languageCode == locale.languageCode) return;
    await _store.write(locale.languageCode);
    _locale = Locale(locale.languageCode);
    notifyListeners();
  }

  Future<void> toggle() => setLocale(
    _locale.languageCode == 'ar' ? const Locale('en') : const Locale('ar'),
  );

  static void _validate(String languageCode) {
    if (!supportedLanguageCodes.contains(languageCode)) {
      throw ArgumentError.value(
        languageCode,
        'languageCode',
        'must be ar or en',
      );
    }
  }
}
