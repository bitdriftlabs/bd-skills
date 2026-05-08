# Android (Kotlin/Java) Integration

This file provides the workflow and placement guidance. For exact API signatures and code examples, use $bd-docs to look up the relevant topic at each step.

---

## Detect project structure

Run these before making any changes — they determine syntax choices and which integrations to recommend:

```bash
# Build system: Groovy (.gradle) vs Kotlin DSL (.gradle.kts)
ls app/build.gradle app/build.gradle.kts 2>/dev/null

# Version catalog (modern AGP projects)
ls gradle/libs.versions.toml 2>/dev/null

# Existing bitdrift SDK
grep -ri "io.bitdrift\|bitdrift" app/build.gradle* build.gradle* gradle/libs.versions.toml 2>/dev/null | head -5

# Language: Kotlin vs Java
find app/src/main -name "*.kt" 2>/dev/null | head -3
find app/src/main -name "*.java" 2>/dev/null | head -3

# Libraries that have dedicated bitdrift integrations
grep -iE "timber|okhttp|retrofit|apollographql" app/build.gradle* gradle/libs.versions.toml 2>/dev/null | head -10

# WebViews (experimental auto-instrumentation available)
grep -rE "WebView|webview" app/src/main --include="*.kt" --include="*.java" --include="*.xml" 2>/dev/null | head -5

# Application class (where Logger.start() goes)
find app/src/main -name "*.kt" -o -name "*.java" 2>/dev/null | xargs grep -l "Application()\|: Application" 2>/dev/null | head -3
```

**What to determine:**

| Signal | Impact |
|--------|--------|
| `build.gradle.kts` present | Use Kotlin DSL syntax in all examples |
| `build.gradle` (no `.kts`) present | Use Groovy DSL syntax in all examples |
| `gradle/libs.versions.toml` present | Add bitdrift to the version catalog; reference via `libs.*` in build files |
| No version catalog | Use direct dependency declarations in build.gradle |
| Existing `io.bitdrift` entries | SDK already installed — skip to instrumentation categories |
| Timber detected | Recommend `capture-timber` integration |
| OkHttp / Retrofit detected | Recommend OkHttp auto-instrumentation via Gradle plugin |
| Apollo GraphQL detected | Recommend `capture-apollo` integration |
| WebView detected | Mention experimental WebView auto-instrumentation option |
| No Application subclass | Will need to create one for `Logger.start()` |
| Java-only source files | Provide Java examples (not Kotlin) |
| Mixed Java/Kotlin | Prefer Kotlin for new code; provide Java if touching existing Java files |

### Legacy / older native Android apps

Many production apps use older build configurations. Handle these correctly:

- **Groovy `build.gradle`** (no `.kts`): Use Groovy syntax for all dependency and plugin declarations
- **No version catalog**: Add dependencies directly in `app/build.gradle` — do not create `libs.versions.toml`
- **Java-first apps**: Provide Java examples for SDK initialization and instrumentation
- **Missing Application class**: Create one and register it in `AndroidManifest.xml`
- **Dependency conflicts** (common with Firebase/Firestore): If `com.google.firebase:firebase-firestore` is present, exclude `protolite-well-known-types` from the bitdrift dependency to avoid duplicate class errors:

```groovy
// Groovy
implementation('io.bitdrift:capture:<version>') {
    exclude group: 'com.google.protobuf', module: 'protolite-well-known-types'
}
```

```kotlin
// Kotlin DSL
implementation("io.bitdrift:capture:<version>") {
    exclude(group = "com.google.protobuf", module = "protolite-well-known-types")
}
```

- **minSdk < 23**: bitdrift requires API 23+. If the app targets lower, note this to the user and suggest raising minSdk or using a manifest merger override for the bitdrift library only.

---

## New installation

Only needed when the SDK is not yet in the project. This adds the dependency and gets `Logger.start()` running. Once verified, move to the instrumentation categories below.

**After every build:** check for type name conflicts introduced by the Capture SDK (common: `Configuration`, `Logger`). Fix by qualifying existing types with their module name before asking the user to rebuild.

### Step 1 — Get the SDK key

Ask the user for their bitdrift SDK key (found in the bitdrift portal under Company Settings → SDK Keys). Tell the user you're ready and ask for confirmation before proceeding.

### Step 2 — SDK dependency

Add the Capture SDK as a Gradle dependency.

**$bd-docs:** look up `android quickstart gradle capture`

**Finding the latest version:** Query Maven Central for the latest published version:

```bash
curl -s "https://central.sonatype.com/solrsearch/select?q=g:io.bitdrift+AND+a:capture&sort=v+desc&rows=1&wt=json"
```

The response JSON contains `response.docs[0].v` with the latest version (e.g., `0.22.16`). Use this in the dependency declaration below.

**If `gradle/libs.versions.toml` detected:** Add entries to the version catalog first, then reference via `libs.*`:

```toml
[versions]
bitdrift = "<version>"

[libraries]
bitdrift-capture = { module = "io.bitdrift:capture", version.ref = "bitdrift" }

[plugins]
bitdrift-capture = { id = "io.bitdrift.capture-plugin", version.ref = "bitdrift" }
```

Then in `app/build.gradle.kts`: `implementation(libs.bitdrift.capture)` and `alias(libs.plugins.bitdrift.capture)`.

**If no version catalog (direct dependencies):**
- Add `io.bitdrift:capture:<version>` to `app/build.gradle.kts` (or `.gradle`)
- Add `io.bitdrift.capture-plugin` to the `plugins {}` block

**Both paths:**
- The Gradle plugin enables auto network instrumentation + ProGuard/R8 mapping upload
- Min SDK: API 23

**Verify:** Ask the user to build. Confirm it compiles cleanly — no unresolved dependencies or type errors.

### Step 3 — SDK initialization

Add the SDK import and call `Logger.start()` at app launch. Start with a **fixed session strategy** — it creates a new session on every launch, making it easy to verify each build.

**$bd-docs:** look up `Logger.start session strategy configuration`

**Placement tips:**
- Call `Logger.start()` in `Application.onCreate()` — before any other initialization
- If using Jetpack Startup, add `ContextHolder` as a dependency in your `Initializer`
- If disabling auto-init, call `AppInitializer.getInstance(applicationContext).initializeComponent(ContextHolder::class.java)` before `Logger.start()`
- Start with `SessionStrategy.Fixed` for easy verification (new session per launch)

**Verify:** Ask the user to build and run the app on an emulator or device, then check logcat for SDK initialization. Filter with:

```
adb logcat | grep -i "bd_"
```

**Success** — look for these logs (in order):
1. `bd_logger::builder` — `bitdrift Capture SDK: "<version>"` (SDK loaded)
2. `bd_device` — `bitdrift Capture device ID: "<uuid>"` (device registered)
3. `bd_logger::builder` — `Successfully acquired directory lock for SDK directory` (storage ready)
4. `bd_session::fixed` or `bd_session::activity_based` — `bitdrift Capture initialized with session ID: "<uuid>"` (session started)

**Failure — bad API key:**
- `bd_api::api` — `failed to authenticate with the backend: invalid API key in x-bitdrift-api-key`
- Fix: double-check the SDK key string passed to `Logger.start()`. Keys are found in the bitdrift portal under Company Settings → SDK Keys.

Once you see the session ID log, the SDK is running. Offer the user two options to confirm the session reached the backend:

1. **Open in browser** — use $bd-cli: `bd timeline open <session_id>` (opens the session in the bitdrift web UI)
2. **Inspect from CLI** — use $bd-cli: `bd timeline logs <session_id>` (fetches the session timeline directly)

Extract the session ID from the `bd_session::fixed` or `bd_session::activity_based` log line. Either option confirms end-to-end connectivity.

---

## Recommend integrations

Based on the detection phase, propose a concrete plan. Lead with what you found:

| Detected | Recommend |
|----------|-----------|
| Timber | Log forwarding via `capture-timber` — captures existing logs with zero new call sites |
| OkHttp / Retrofit | Network monitoring via Gradle plugin auto-instrumentation |
| Apollo GraphQL | Network monitoring via `capture-apollo` interceptor |
| WebView | WebView monitoring via Gradle plugin auto-instrumentation (experimental) |
| Fragment / Activity navigation | Screen view tracking at navigation points |
| None of the above | Manual log forwarding + manual HTTP logging |

**If the user explicitly named categories in their prompt, implement those categories directly without asking.** Only present a choice when the user's request is vague (e.g., "add bitdrift" with no specifics).

---

## Instrumentation categories

Each category is standalone. Jump directly to whichever one the user needs — whether they just finished a new install or already had the SDK set up. For each, fetch the API details from docs first.

### Log forwarding

Forward existing logs from Timber (or other logging wrappers) to bitdrift. This captures existing instrumentation with no new log call sites needed.

**Detect Timber:** Search the project for `timber` in `build.gradle.kts` / `build.gradle` dependencies, or `import timber.log.Timber` in source files.

**If Timber is detected:**

**$bd-docs:** look up `timber integrations log forwarding`

Find the latest `capture-timber` version:

```bash
curl -s "https://central.sonatype.com/solrsearch/select?q=g:io.bitdrift+AND+a:capture-timber&sort=v+desc&rows=1&wt=json"
```

Read `response.docs[0].v` for the version. Then:

- Add `io.bitdrift:capture-timber:<version>` dependency
- Call `Timber.plant(CaptureTree())` after `Logger.start()`

**If no Timber:** Forward logs manually in the existing logging wrapper, matching the source level to the correct bitdrift method:

| Source level | bitdrift method |
|---|---|
| `Log.v` / verbose | `Logger.logTrace { msg }` |
| `Log.d` / debug | `Logger.logDebug { msg }` |
| `Log.i` / info | `Logger.logInfo { msg }` |
| `Log.w` / warn | `Logger.logWarning { msg }` |
| `Log.e` / error | `Logger.logError { msg }` |

Preserving level semantics keeps bitdrift workflows and filters meaningful — an `error` in the source should be an `error` in bitdrift.

**Verify:** Build and run, confirm log messages appear in the bitdrift timeline.

### Network monitoring

Instrument HTTP traffic automatically. **Always prefer the Gradle plugin auto-instrumentation** — it instruments all OkHttp clients without code changes and includes tracing.

**Pick one approach — never both.** The Gradle plugin auto-instrumentation and the manual `CaptureOkHttpEventListenerFactory` both attach an event listener to `OkHttpClient`. Using both causes duplicate instrumentation — every request gets logged twice, metrics are doubled, and spans overlap. Choose the Gradle plugin path (recommended) or the manual path, but never combine them in the same project.

**Detect libraries:** Search `build.gradle.kts` / `build.gradle` dependencies for:

| Signal | Library |
|--------|---------|
| `com.squareup.okhttp3:okhttp` or `okhttp3` imports | **OkHttp** |
| `com.apollographql.apollo3` or `com.apollographql.apollo` | **Apollo GraphQL** |

**If OkHttp is detected (preferred path — auto-instrumentation via Gradle plugin):**

**$bd-docs:** fetch `https://docs.bitdrift.io/sdk/integrations.md` and read the **OkHttp > Auto-Instrumentation via Gradle Plugin** section for the exact DSL and setup steps.

1. Ensure the `io.bitdrift.capture-plugin` Gradle plugin is applied (should already be from Step 2)
2. Enable `automaticOkHttpInstrumentation = true` in the `bitdrift { instrumentation { } }` DSL block at the bottom of the app-level build file — use the exact syntax from the docs, matching the project's build system (Kotlin DSL vs Groovy)
3. This instruments all `OkHttpClient` instances via bytecode manipulation — no manual interceptor or event listener needed
4. Verify no `CaptureOkHttpEventListenerFactory` calls exist in the codebase — remove them if found, since the plugin handles everything

**If auto-instrumentation can't be used** (e.g., no Gradle plugin, or the project needs a custom `EventListener.Factory`): Use manual instrumentation instead — read the **OkHttp > Manual Instrumentation** section from the same docs page. Add `CaptureOkHttpEventListenerFactory` to each `OkHttpClient.Builder`, and do NOT enable `automaticOkHttpInstrumentation` in the Gradle plugin.

**If the project uses Retrofit with OkHttp:** Also read the **Using with Retrofit** section from the same docs page — it describes `RetrofitUrlPathProvider` for extracting endpoint URL paths from Retrofit service annotations, which improves the quality of network logs. Only relevant for manual instrumentation (auto-instrumentation handles this automatically).

**If Apollo GraphQL is detected:**

**$bd-docs:** fetch `https://docs.bitdrift.io/sdk/integrations.md` and read the **Apollo GraphQL** section under Networking for installation and usage.

Find the latest `capture-apollo` version:

```bash
curl -s "https://central.sonatype.com/solrsearch/select?q=g:io.bitdrift+AND+a:capture-apollo&sort=v+desc&rows=1&wt=json"
```

Read `response.docs[0].v` for the version. Then:

- Add `io.bitdrift:capture-apollo:<version>` dependency
- Add the `CaptureApolloInterceptor` to your `ApolloClient.Builder`
- OkHttp instrumentation (auto or manual) is also required alongside Apollo — see docs for the combined setup

**If neither OkHttp nor Apollo:** Use the manual HTTP logging API — **$bd-docs:** look up `http traffic logs manual`

**If WebViews are present:** The Capture Gradle plugin can also auto-instrument Android `WebView` instances (experimental). **$bd-docs:** fetch `https://docs.bitdrift.io/sdk/integrations.md` and read the **WebView (Android)** section for setup and `WebViewConfiguration` options.

**Verify:** Trigger a network request and confirm HTTP events appear in the timeline.

### Screen views

Track navigation to power Sankey diagrams, funnels, and user journeys. **Every navigable screen must be instrumented** — partial coverage breaks funnels and journey analysis.

**$bd-docs:** look up `screen view automatic instrumentation`

**Strategy by navigation type:**

| Navigation pattern | Approach |
|----|-----|
| Jetpack Navigation (NavController) | `NavController.addOnDestinationChangedListener` — single centralized listener covers all destinations |
| Fragment-based (without NavController) | Add `Logger.logScreenView("ScreenName")` in each `Fragment.onResume()`, or use a shared `FragmentLifecycleCallbacks` registered in `Application.onCreate()` |
| Activity-based | Add `Logger.logScreenView("ScreenName")` in each `Activity.onResume()` |
| Jetpack Compose | `LaunchedEffect(Unit)` or `DisposableEffect` in each screen composable, or a centralized `NavController.addOnDestinationChangedListener` |

**Requirements:**
- Instrument ALL screens, not just the launch screen
- Use descriptive, stable screen names (e.g., `"RecipeDetail"`, `"Settings"`, `"Search"`)
- Report to the user any screens that could not be automatically covered

**Verify:** Navigate between screens and confirm `_screen_view` events appear for each transition.

### TTI (Time to Interactive)

Record how long the app takes to become interactive after a cold launch.

**$bd-docs:** look up `TTI app launch time interactive`

- Record the start time at the beginning of `Application.onCreate()`
- Call `Logger.logAppLaunchTTI(duration)` once the first meaningful frame is rendered or the user can interact
- Call exactly once per cold launch

**Verify:** Cold-launch the app and confirm `_app_launch_tti` appears with a plausible duration.

### Structured fields and user identity

Attach metadata to all subsequent logs. Most commonly used for user identity after authentication.

**$bd-docs:** look up `fields addField`

- Set identity fields after login or session restore using `Logger.addField("user_id", user_id)`
- On logout or account switch, set updated values (fields are overwritten by key)
- Set any additional fields iwth valuable global metadata using `Logger.addField("key", value)`
- Field names starting with `_` are reserved by bitdrift

### Spans

Instrument discrete operations with start/end timing (API calls, rendering, checkout flow).

**$bd-docs:** look up `spans startSpan`

- `Logger.startSpan(name, level, fields)` / `span.end(result)`
- Use `Logger.trackSpan("name", level) { ... }` for auto-close

### Feature flag exposure

Record which variant a user sees at the moment of divergence.

**$bd-docs:** look up `feature flag exposure`

- Record at the **moment of divergence** — when the flag value affects what the user sees

### ProGuard / R8 mapping upload

**$bd-docs:** look up `proguard mapping debug symbols`

- The Gradle plugin handles automatic upload when configured

### Analytics event forwarding

Forward existing analytics events (Amplitude, custom event client, etc.) to bitdrift at the single submission point:

```kotlin
Logger.logInfo(mapOf("analytics_event_name" to eventName) + eventProperties.mapKeys { "analytics_${it.key}" }) { "analytics_event" }
```
