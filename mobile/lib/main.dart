import 'package:flutter/material.dart';

import 'read_model_contract.dart';
import 'src/client/secure_guide_client.dart';
import 'src/screens/assessment_screen.dart';
import 'src/screens/catalog_screen.dart';
import 'src/screens/dashboard_screen.dart';

void main() {
  runApp(SecureGuideApp(client: HttpSecureGuideClient()));
}

class SecureGuideApp extends StatelessWidget {
  const SecureGuideApp({super.key, required this.client});

  final SecureGuideClient client;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SecureGuide',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF1F4E79),
        useMaterial3: true,
      ),
      // The contract carries Arabic content; force RTL until full localization
      // delegates land (Phase 2).
      builder: (context, child) =>
          Directionality(textDirection: TextDirection.rtl, child: child!),
      home: HomeShell(client: client),
    );
  }
}

/// The app shell: pick an enterprise profile, then show its dashboard.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key, required this.client});

  final SecureGuideClient client;

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

  @override
  Widget build(BuildContext context) {
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
            appBar: AppBar(title: const Text('SecureGuide')),
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'تعذّر الوصول إلى الخدمة المحلية.\n'
                  'شغّل: python -m secureguide.sidecar\n\n${snapshot.error}',
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          );
        }

        final profiles = snapshot.data!.profiles;
        if (profiles.isEmpty) {
          return Scaffold(
            appBar: AppBar(title: const Text('SecureGuide')),
            body: const Center(child: Text('لا توجد ملفات مؤسسية بعد.')),
          );
        }

        final selected = _resolveSelected(profiles);
        return Scaffold(
          appBar: AppBar(
            title: Text(selected.name ?? 'SecureGuide'),
            actions: [
              IconButton(
                icon: const Icon(Icons.library_books_outlined),
                tooltip: 'الكتالوج',
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => CatalogScreen(
                      client: widget.client,
                      profileId: selected.id,
                    ),
                  ),
                ),
              ),
              _profileMenu(profiles, selected),
            ],
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: () => _createProfile(context),
            tooltip: 'ملف مؤسسي جديد',
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
        SnackBar(content: Text('تعذّر إنشاء الملف: $error')),
      );
    }
  }

  Future<void> _selectProfile(String profileId) async {
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
        SnackBar(content: Text('تعذّر تفعيل الملف: $error')),
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
    return PopupMenuButton<String>(
      icon: const Icon(Icons.account_tree_outlined),
      tooltip: 'اختيار الملف',
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
    return AlertDialog(
      title: const Text('ملف مؤسسي جديد'),
      content: TextField(
        controller: _controller,
        autofocus: true,
        decoration: const InputDecoration(labelText: 'اسم الملف'),
        onSubmitted: (value) => Navigator.of(context).pop(value),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('إلغاء'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(_controller.text),
          child: const Text('إنشاء'),
        ),
      ],
    );
  }
}
