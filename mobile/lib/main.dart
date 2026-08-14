import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'core/localization/locale_controller.dart';
import 'l10n/app_localizations.dart';
import 'read_model_contract.dart';
import 'src/client/local_secure_guide_client.dart';
import 'src/client/secure_guide_client.dart';
import 'src/screens/assessment_screen.dart';
import 'src/screens/catalog_screen.dart';
import 'src/screens/dashboard_screen.dart';
import 'src/screens/exceptions_screen.dart';
import 'src/screens/profile_settings_screen.dart';
import 'src/screens/tasks_screen.dart';
import 'src/screens/template_list_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(SecureGuideApp(client: LocalSecureGuideClient()));
}

class SecureGuideApp extends StatefulWidget {
  const SecureGuideApp({
    super.key,
    required this.client,
    this.localeController,
  });

  final SecureGuideClient client;
  final LocaleController? localeController;

  @override
  State<SecureGuideApp> createState() => _SecureGuideAppState();
}

class _SecureGuideAppState extends State<SecureGuideApp> {
  late final LocaleController _localeController;
  late final bool _ownsLocaleController;

  @override
  void initState() {
    super.initState();
    _ownsLocaleController = widget.localeController == null;
    _localeController = widget.localeController ?? LocaleController();
    if (_ownsLocaleController) unawaited(_loadLocale());
  }

  Future<void> _loadLocale() async {
    try {
      await _localeController.load();
    } catch (error, stackTrace) {
      FlutterError.reportError(
        FlutterErrorDetails(
          exception: error,
          stack: stackTrace,
          library: 'SecureGuide localization',
          context: ErrorDescription('while loading the persisted locale'),
        ),
      );
    }
  }

  @override
  void dispose() {
    if (_ownsLocaleController) _localeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _localeController,
      builder: (context, _) => MaterialApp(
        onGenerateTitle: (context) => AppLocalizations.of(context)!.appTitle,
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorSchemeSeed: const Color(0xFF1F4E79),
          fontFamily: 'Tajawal',
          useMaterial3: true,
        ),
        locale: _localeController.locale,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: HomeShell(
          client: widget.client,
          localeController: _localeController,
        ),
      ),
    );
  }
}

/// The app shell: pick an enterprise profile, then show its dashboard.
class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.client,
    required this.localeController,
  });

  final SecureGuideClient client;
  final LocaleController localeController;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  late Future<ProfilesView> _future;
  String? _selectedId;

  @override
  void initState() {
    super.initState();
    _future = widget.client.profiles();
  }

  void _loadProfiles() {
    setState(() {
      _future = widget.client.profiles();
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return FutureBuilder<ProfilesView>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        if (snapshot.hasError) {
          return Scaffold(
            appBar: AppBar(
              title: Text(l10n.appTitle),
              actions: [_languageButton()],
            ),
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  l10n.localDataOpenError(snapshot.error!),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          );
        }

        final profiles = snapshot.data!.profiles;
        if (profiles.isEmpty) {
          return Scaffold(
            appBar: AppBar(
              title: Text(l10n.appTitle),
              actions: [_languageButton()],
            ),
            body: Center(child: Text(l10n.noProfiles)),
            floatingActionButton: FloatingActionButton(
              key: const Key('create-profile'),
              heroTag: 'create-profile-empty',
              onPressed: () => _createProfile(context),
              tooltip: l10n.createProfileTooltip,
              child: const Icon(Icons.add),
            ),
          );
        }

        final selected = _resolveSelected(profiles);
        final activeId = selected.id;
        return Scaffold(
          appBar: AppBar(
            title: Text(selected.name ?? 'SecureGuide'),
            actions: [
              _languageButton(),
              IconButton(
                key: const Key('open-catalog'),
                icon: const Icon(Icons.add_circle_outline),
                tooltip: l10n.catalog,
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => CatalogScreen(
                        client: widget.client,
                        profileId: activeId,
                      ),
                    ),
                  );
                  _loadProfiles();
                },
              ),
              IconButton(
                icon: const Icon(Icons.check_box_outlined),
                tooltip: l10n.tasks,
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => TasksScreen(
                        client: widget.client,
                        profileId: activeId!,
                      ),
                    ),
                  );
                  _loadProfiles();
                },
              ),
              IconButton(
                icon: const Icon(Icons.file_copy_outlined),
                tooltip: l10n.templates,
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => TemplateListScreen(
                        client: widget.client,
                        profileId: activeId!,
                      ),
                    ),
                  );
                  _loadProfiles();
                },
              ),
              IconButton(
                icon: const Icon(Icons.rule),
                tooltip: l10n.exceptionLog,
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => ExceptionsScreen(
                        client: widget.client,
                        profileId: activeId!,
                      ),
                    ),
                  );
                  _loadProfiles();
                },
              ),
              _profileMenu(profiles, selected),
              IconButton(
                icon: const Icon(Icons.settings),
                tooltip: l10n.profileSettings,
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => ProfileSettingsScreen(
                        client: widget.client,
                        profileId: activeId!,
                        onProfileArchived: () {
                          Navigator.of(context).pop();
                        },
                      ),
                    ),
                  );
                  _loadProfiles();
                },
              ),
            ],
          ),
          floatingActionButton: FloatingActionButton(
            key: const Key('create-profile'),
            heroTag: 'create-profile-active',
            onPressed: () => _createProfile(context),
            tooltip: l10n.createProfileTooltip,
            child: const Icon(Icons.add),
          ),
          body: DashboardScreen(
            key: ValueKey(selected.id),
            client: widget.client,
            profileId: selected.id,
            onAssess: (artifactId) => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => AssessmentScreen(
                  client: widget.client,
                  artifactId: artifactId,
                  profileId: selected.id,
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _createProfile(BuildContext context) async {
    final l10n = AppLocalizations.of(context)!;
    final messenger = ScaffoldMessenger.of(context);
    final name = await showDialog<String>(
      context: context,
      builder: (_) => const _CreateProfileDialog(),
    );
    if (name == null || name.trim().isEmpty) return;
    try {
      final created = await widget.client.createProfile(
        name: name.trim(),
        activate: true,
      );
      if (!mounted) return;
      setState(() {
        _selectedId = created.id;
        _future = widget.client.profiles();
      });
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.profileCreateError(error))),
      );
    }
  }

  Future<void> _selectProfile(String profileId) async {
    final l10n = AppLocalizations.of(context)!;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await widget.client.activateProfile(profileId);
      if (!mounted) return;
      setState(() {
        _selectedId = profileId;
        _future = widget.client.profiles();
      });
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.profileActivateError(error))),
      );
    }
  }

  ProfileSummary _resolveSelected(List<ProfileSummary> profiles) {
    for (final profile in profiles) {
      if (profile.id == _selectedId) return profile;
    }
    for (final profile in profiles) {
      if (profile.isActive == true) return profile;
    }
    return profiles.first;
  }

  Widget _profileMenu(List<ProfileSummary> profiles, ProfileSummary selected) {
    final l10n = AppLocalizations.of(context)!;
    return PopupMenuButton<String>(
      icon: const Icon(Icons.account_tree_outlined),
      tooltip: l10n.chooseProfile,
      initialValue: selected.id,
      onSelected: _selectProfile,
      itemBuilder: (context) => [
        for (final profile in profiles)
          PopupMenuItem<String>(
            value: profile.id,
            child: Text(profile.name ?? profile.id ?? '—'),
          ),
      ],
    );
  }

  Widget _languageButton() {
    final l10n = AppLocalizations.of(context)!;
    final isArabic = widget.localeController.locale.languageCode == 'ar';
    return IconButton(
      key: const Key('locale-toggle'),
      icon: const Icon(Icons.translate),
      tooltip: isArabic ? l10n.switchToEnglish : l10n.switchToArabic,
      onPressed: () async {
        final messenger = ScaffoldMessenger.of(context);
        try {
          await widget.localeController.toggle();
        } catch (error) {
          if (!mounted) return;
          messenger.showSnackBar(
            SnackBar(content: Text(l10n.localeChangeError(error))),
          );
        }
      },
    );
  }
}

/// Minimal name prompt for creating an enterprise profile. Returns the entered
/// name via [Navigator.pop], or null on cancel.
class _CreateProfileDialog extends StatefulWidget {
  const _CreateProfileDialog();

  @override
  State<_CreateProfileDialog> createState() => _CreateProfileDialogState();
}

class _CreateProfileDialogState extends State<_CreateProfileDialog> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return AlertDialog(
      title: Text(l10n.createProfileTitle),
      content: TextField(
        key: const Key('profile-name'),
        controller: _controller,
        autofocus: true,
        decoration: InputDecoration(labelText: l10n.profileName),
        onSubmitted: (value) => Navigator.of(context).pop(value),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('create-profile-submit'),
          onPressed: () => Navigator.of(context).pop(_controller.text),
          child: Text(l10n.create),
        ),
      ],
    );
  }
}
