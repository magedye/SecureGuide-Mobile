import org.gradle.api.GradleException

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

val releaseStorePath = System.getenv("SECUREGUIDE_ANDROID_KEYSTORE_PATH")?.trim()
val releaseStorePassword = System.getenv("SECUREGUIDE_ANDROID_KEYSTORE_PASSWORD")?.trim()
val releaseKeyAlias = System.getenv("SECUREGUIDE_ANDROID_KEY_ALIAS")?.trim()
val releaseKeyPassword = System.getenv("SECUREGUIDE_ANDROID_KEY_PASSWORD")?.trim()
val releaseSigningValues = listOf(
    releaseStorePath,
    releaseStorePassword,
    releaseKeyAlias,
    releaseKeyPassword,
)
val hasAnyReleaseSigningValue = releaseSigningValues.any { !it.isNullOrEmpty() }
val hasCompleteReleaseSigningValues = releaseSigningValues.all { !it.isNullOrEmpty() }
val requireReleaseSigning =
    System.getenv("SECUREGUIDE_REQUIRE_RELEASE_SIGNING")?.equals("true", ignoreCase = true) == true

if (hasAnyReleaseSigningValue && !hasCompleteReleaseSigningValues) {
    throw GradleException(
        "SecureGuide release signing is partially configured; provide all four signing inputs.",
    )
}
if (requireReleaseSigning && !hasCompleteReleaseSigningValues) {
    throw GradleException("SecureGuide release signing is required but no complete key configuration was supplied.")
}
if (hasCompleteReleaseSigningValues && !file(releaseStorePath!!).isFile) {
    throw GradleException("SecureGuide release keystore does not exist at the configured path.")
}

val secureGuideApplicationId =
    System.getenv("SECUREGUIDE_APPLICATION_ID")?.trim()?.takeIf { it.isNotEmpty() }
        ?: "com.example.secureguide_mobile"
val androidApplicationId = Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z][A-Za-z0-9_]*)+$")
if (!androidApplicationId.matches(secureGuideApplicationId)) {
    throw GradleException("SECUREGUIDE_APPLICATION_ID is not a valid Android application ID.")
}
if (requireReleaseSigning && secureGuideApplicationId.startsWith("com.example.")) {
    throw GradleException("A signed release must use an owner-approved application ID, not com.example.*.")
}

android {
    namespace = "com.example.secureguide_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        // Unsigned compile verification retains the generated placeholder. The
        // protected release workflow must supply the owner-approved identity.
        applicationId = secureGuideApplicationId
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    val secureGuideReleaseSigning = if (hasCompleteReleaseSigningValues) {
        signingConfigs.create("secureGuideRelease") {
            storeFile = file(releaseStorePath!!)
            storePassword = releaseStorePassword
            keyAlias = releaseKeyAlias
            keyPassword = releaseKeyPassword
        }
    } else {
        null
    }

    buildTypes {
        getByName("release") {
            // Never fall back to the debug key. An ordinary CI compile remains
            // unsigned; the protected release workflow requires this config.
            signingConfig = secureGuideReleaseSigning
        }
    }
}

flutter {
    source = "../.."
}
