---
name: bd-instrumentation
description: "Mobile app instrumentation and Capture SDK setup for bitdrift in iOS, Android, and React Native apps, including new installs and extending existing integrations with screen tracking, network monitoring, logs, fields, and spans."
---

# bitdrift Instrumentation

Guides integration of the bitdrift Capture SDK into mobile apps. The SDK logs everything locally on-device; the bitdrift control plane dynamically decides what to upload.

## How this skill uses docs

Use $bd-docs to fetch live API details from docs.bitdrift.io at each step. The platform reference files indicate what to look up — $bd-docs handles the mechanics of discovery and fetching.

## Workflow summary

Detect platform → Check if SDK is installed → Read platform reference → If new install: add dependency + `Logger.start()` → Add instrumentation categories the user needs.

## Step 1 — Detect platform

Identify the target platform from the user's project:

| Signal | Platform |
|--------|----------|
| `build.gradle`, `build.gradle.kts`, `.kt`, `.java`, `AndroidManifest.xml` | **Android** |
| `.xcodeproj`, `.xcworkspace`, `Package.swift`, `Podfile`, `.swift`, `.m`/`.h` | **iOS** |
| `package.json` with `react-native`, `metro.config.js`, `App.tsx`/`App.js` | **React Native** |

If the project contains files for multiple platforms (e.g., both Android and React Native in a monorepo), ask the user which target to instrument.

## Step 2 — Determine SDK status

Check whether the bitdrift Capture SDK is already installed by searching the project for:

| Platform | SDK already present if you find… |
|----------|----------------------------------|
| Android | `io.bitdrift:capture` in `build.gradle`/`build.gradle.kts`, or `import io.bitdrift.capture` in source |
| iOS | `capture-ios` in `Package.swift` or `BitdriftCapture` in `Podfile`, or `import Capture` in source |
| React Native | `@bitdrift/react-native` in `package.json`, or `import { init } from '@bitdrift/react-native'` in source |

## Step 3 — Read the platform reference and proceed

Read the platform reference file, then follow the appropriate path:

| Platform | Reference file |
|----------|---------------|
| Android (Kotlin/Java) | `references/android.md` in this skill directory |
| iOS (Swift/Objective-C) | `references/ios.md` in this skill directory |
| React Native | `references/react-native.md` in this skill directory |

Each reference file has two sections:

- **New installation** — Add the SDK dependency and call `Logger.start()`. Follow this when the SDK is not yet present. Once the SDK is running, proceed to the instrumentation categories below.
- **Instrumentation categories** — Standalone enhancements (log forwarding, network monitoring, screen views, TTI, fields, spans, etc.). Each is independent — jump directly to whichever one the user needs. These apply whether the user just finished a new install or already had the SDK set up.

## Validation checklist (all platforms)

When asked to validate an integration, check all items and produce a report with PASS/FAIL/WARNING per check, plus concrete code fixes for failures.

| # | Check |
|---|-------|
| 1 | SDK dependency present and up to date |
| 2 | Logger initialized early in app lifecycle |
| 3 | Session strategy configured |
| 4 | Network monitoring active |
| 5 | Screen tracking on every screen |
| 6 | TTI tracked |
| 7 | Crash reporter linked with session URL |
| 8 | User identity fields set after login |
| 9 | dSYM/ProGuard mapping upload configured (if applicable) |
