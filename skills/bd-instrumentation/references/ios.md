# iOS (Swift/Objective-C) Integration

This file provides the workflow and placement guidance. For exact API signatures and code examples, use $bd-docs to look up the relevant topic at each step.

---

## Detect project structure

Run these before making any changes — they determine dependency setup, init pattern, and which integrations to recommend:

```bash
# Dependency manager
ls Podfile Podfile.lock Package.swift 2>/dev/null
grep -l "XCRemoteSwiftPackageReference" *.xcodeproj/project.pbxproj 2>/dev/null

# Existing bitdrift SDK
grep -iE "bitdrift|BitdriftCapture|capture-ios" Package.swift Podfile 2>/dev/null
grep -rE "import Capture$" --include="*.swift" . 2>/dev/null | head -3

# Language: Swift vs Objective-C
find . -name "*.swift" -not -path "*/Pods/*" 2>/dev/null | head -3
find . -name "*.m" -not -path "*/Pods/*" 2>/dev/null | head -3

# UI framework: SwiftUI vs UIKit
grep -rE "@main.*App|struct.*:.*App" --include="*.swift" . 2>/dev/null | head -3
grep -rE "AppDelegate|UIApplicationMain|@UIApplicationMain" --include="*.swift" . 2>/dev/null | head -3

# Libraries that have dedicated bitdrift integrations
grep -riE "CocoaLumberjack|DDLog|SwiftyBeaver" --include="*.swift" Podfile Package.swift 2>/dev/null | head -5
grep -riE "Alamofire|URLSession" --include="*.swift" . 2>/dev/null | head -5
```

**What to determine:**

| Signal | Impact |
|--------|--------|
| `Podfile` present | CocoaPods path — use `pod 'BitdriftCapture'` |
| `Package.swift` or SPM references in `.xcodeproj` | SPM path — add `capture-ios` package |
| `.m`/`.h` files present | Objective-C — use `CAPLogger` APIs |
| `@main struct ... App` pattern | SwiftUI — init in `App.init()` |
| `AppDelegate` present | UIKit — init in `didFinishLaunchingWithOptions` |
| Existing `import Capture` or `BitdriftCapture` in Podfile | SDK already installed — skip to instrumentation categories |
| CocoaLumberjack / SwiftyBeaver detected | Recommend log forwarding integration |
| Network code detected (URLSession / Alamofire) | Recommend network monitoring |

---

## New installation

Only needed when the SDK is not yet in the project. This adds the dependency and gets `Logger.start()` running. Once verified, move to the instrumentation categories below.

**After every build:** check for type name conflicts introduced by the Capture SDK (common: `Configuration`, `Logger`). Fix by qualifying existing types with their module name (e.g., `OSLog.Logger`, `WMF.Configuration`) before asking the user to rebuild.

### Step 1 — Get the SDK key

Ask the user for their bitdrift SDK key (found in the bitdrift portal under Company Settings → SDK Keys). Tell the user you're ready and ask for confirmation before proceeding.

### Step 2 — SDK dependency

Detect the dependency manager by checking the project root:

| Signal | Manager |
|--------|---------|
| `Podfile` or `Podfile.lock` present | **CocoaPods** |
| `Package.swift` present, or `.xcodeproj` contains `XCRemoteSwiftPackageReference` | **SPM** |
| Both present | Prefer whichever manages the majority of deps; ask the user if unclear |

Then fetch the matching installation instructions and find the latest version:

- **SPM detected →** **$bd-docs:** look up `iOS quickstart SPM swift package`
  - **Latest version:** Fetch the current release tag:
    ```bash
    curl -s "https://api.github.com/repos/bitdriftlabs/capture-ios/releases/latest"
    ```
    Read `tag_name` from the JSON response — this is the version to use when setting the package dependency rule (e.g., "Up to Next Major Version").

- **CocoaPods detected →** **$bd-docs:** look up `iOS quickstart CocoaPods pod`
  - **Latest version:** Fetch the current release tag:
    ```bash
    curl -s "https://api.github.com/repos/bitdriftlabs/capture-ios/releases/latest"
    ```
    Read `tag_name` from the JSON response. Pin in the Podfile: `pod 'BitdriftCapture', '~> <version>'`

**Placement tips (SPM):**
- Add `https://github.com/bitdriftlabs/capture-ios.git` package
- For log forwarding integrations, also add the corresponding package product (e.g., `CaptureCocoaLumberjack`)

**Placement tips (CocoaPods):**
- `pod 'BitdriftCapture'` — but the Swift import is `import Capture` (not `BitdriftCapture`)
- For log forwarding integrations, add the corresponding pod (e.g., `pod 'CaptureCocoaLumberjack'`)
- Run `pod install` after editing the Podfile
- **Do not add `BitdriftCapture` to shared framework targets** that are also imported by the main app target — this embeds the SDK in two binaries and causes duplicate ObjC class symbol warnings at runtime. Add Capture only to the targets that call `Logger.start()`.

**Both:**
- Min iOS: 15 — if the project targets iOS 14 or lower, inform the user that the SDK requires iOS 15 and ask for explicit confirmation before bumping the deployment target

**Verify:** Ask the user to build. Confirm it compiles cleanly — no unresolved dependencies or type errors.

### Step 3 — SDK initialization

Add the SDK import and call `Logger.start()` at app launch. Start with a **fixed session strategy** — new session every launch for easy verification.

**$bd-docs:** look up `Logger.start session strategy configuration`

**Placement** — based on the UI framework detected in Phase 1:

- **SwiftUI** (`@main App` struct detected): Call in `init()`
- **UIKit** (`AppDelegate` detected): Call in `application(_:didFinishLaunchingWithOptions:)` or `willFinishLaunchingWithOptions:` — early init allows the SDK to observe system events like `didFinishLaunchingNotification`
- **Objective-C:** use `[CAPLogger startWithAPIKey:sessionStrategy:]`

**Tips:**
- Start with `.fixed()` for easy verification
- The `start()` method returns an optional integrations handle — chain `.enableIntegrations([...])` to set up URLSession, CocoaLumberjack, etc.

**Verify:** Ask the user to build and run the app on a simulator or device, then check the Xcode console for SDK initialization logs. Filter with `bd_` in the console search bar, or from terminal:

```
xcrun simctl spawn booted log stream --predicate 'subsystem CONTAINS "bd_"' --level info
```

**Success** — look for these logs (in order):
1. `bd_logger::builder` — `bitdrift Capture SDK: "<version>"` (SDK loaded)
2. `bd_device` — `bitdrift Capture device ID: "<uuid>"` (device registered)
3. `bd_logger::builder` — `Successfully acquired directory lock for SDK directory` (storage ready)
4. `bd_session::fixed` or `bd_session::activity_based` — `bitdrift Capture initialized with session ID: "<uuid>"` (session started)

**Failure — bad API key:**
- `bd_api::api` — `failed to authenticate with the backend: invalid API key in x-bitdrift-api-key`
- Fix: double-check the SDK key string passed to `Logger.start(withAPIKey:sessionStrategy:)`. Keys are found in the bitdrift portal under Company Settings → SDK Keys.

**Failure — bundle ID not allowlisted:**
- `bd_api::api` — `failed to authenticate with the backend: app_id is not allowed by SDK key`
- Fix: generate a new SDK key scoped to the app's bundle ID, or use a key with a wildcard pattern (e.g. `com.company.*`) that covers it.

**Failure — cached auth failure:**
- `bd_api::api` — `The Capture SDK has been force disabled due to a previous authentication failure or a remote server configuration`
- Fix: uninstall the app from the device/simulator to clear the cached state, then relaunch. Alternatively, changing the API key also resets this state.

Once you see the session ID log, the SDK is running. Offer the user two options to confirm the session reached the backend:

1. **Open in browser** — use $bd-cli: `bd timeline open <session_id>` (opens the session in the bitdrift web UI)
2. **Inspect from CLI** — use $bd-cli: `bd timeline logs <session_id>` (fetches the session timeline directly)

Extract the session ID from the `bd_session::fixed` or `bd_session::activity_based` log line. Either option confirms end-to-end connectivity.

---

## Recommend integrations

Based on the detection phase, propose a concrete plan. Lead with what you found:

| Detected | Recommend |
|----------|-----------|
| CocoaLumberjack | Log forwarding via `CaptureCocoaLumberjack` — captures existing logs automatically |
| SwiftyBeaver | Log forwarding via `CaptureSwiftyBeaver` — captures existing logs automatically |
| URLSession / Alamofire usage | Network monitoring via `.enableIntegrations([.urlSession()])` |
| UIKit navigation (UIViewController) | Screen view tracking in `viewDidAppear` |
| SwiftUI navigation | Screen view tracking via `.onAppear` |
| None of the above | Manual log forwarding + manual screen views |

Present the recommended categories to the user and ask which they want to add. Then jump to the relevant sections below.

---

## Instrumentation categories

Each category is standalone. Jump directly to whichever one the user needs — whether they just finished a new install or already had the SDK set up. For each, fetch the API details from docs first.

### Log forwarding

Forward existing logs from CocoaLumberjack, SwiftyBeaver, or custom wrappers to bitdrift.

**Detect logging library:** Search the project for signals:

| Signal | Library |
|--------|---------|
| `import CocoaLumberjack`, `import CocoaLumberjackSwift`, `DDLog`, pod `CocoaLumberjack` in Podfile, or `CocoaLumberjack` SPM package | **CocoaLumberjack** |
| `import SwiftyBeaver`, `SwiftyBeaver` in Podfile or SPM packages | **SwiftyBeaver** |

**$bd-docs:** look up `CocoaLumberjack SwiftyBeaver integrations log forwarding`

**If CocoaLumberjack is detected:**

Find the latest version:

```bash
curl -s "https://api.github.com/repos/bitdriftlabs/capture-ios/releases/latest"
```

Read `tag_name` from the JSON response. Then:

- **SPM:** Add the `CaptureCocoaLumberjack` package product from the `capture-ios` package
- **CocoaPods:** Add `pod 'CaptureCocoaLumberjack'` and run `pod install`
- Chain `.enableIntegrations([.cocoaLumberjack()])` on `Logger.start()`

**If SwiftyBeaver is detected:**

Find the latest version (same repo):

```bash
curl -s "https://api.github.com/repos/bitdriftlabs/capture-ios/releases/latest"
```

Read `tag_name` from the JSON response. Then:

- **SPM:** Add the `CaptureSwiftyBeaver` package product from the `capture-ios` package
- **CocoaPods:** Add `pod 'BitdriftSwiftyBeaver'` and run `pod install` (note: pod name differs from import)
- Chain `.enableIntegrations([.swiftyBeaver()])` on `Logger.start()`

**If neither:** Forward logs manually in the existing logging wrapper, matching the source level to the correct bitdrift method:

| Source level | bitdrift method |
|---|---|
| verbose / trace | `Logger.logTrace("msg")` |
| debug / `OSLogType.debug` | `Logger.logDebug("msg")` |
| info / notice / `OSLogType.info` / `OSLogType.default` | `Logger.logInfo("msg")` |
| warning | `Logger.logWarning("msg")` |
| error / fault / `OSLogType.error` / `OSLogType.fault` | `Logger.logError("msg")` |

Preserving level semantics keeps bitdrift workflows and filters meaningful — an error in the source should be an error in bitdrift.

**Verify:** Build and run, confirm log messages appear in the bitdrift timeline.

### Network monitoring

Instrument URLSession for automatic HTTP traffic capture.

**$bd-docs:** look up `URLSession network http instrumentation`

- **With swizzling (default):** `.enableIntegrations([.urlSession()])` — instruments all URLSession instances automatically
- **Without swizzling:** `.enableIntegrations([.urlSession()], disableSwizzling: true)` then create sessions using `URLSession(instrumentedSessionWithConfiguration:delegate:delegateQueue:)`
- Alamofire wraps URLSession, so swizzling covers it

**Verify:** Trigger a network request and confirm HTTP events appear in the timeline.

### Screen views

Track navigation to power Sankey diagrams, funnels, and user journeys.

**$bd-docs:** look up `screen view automatic instrumentation`

- **UIKit:** Call `Logger.logScreenView(screenName:)` in `viewDidAppear(_:)` of each view controller
- **SwiftUI:** Use `.onAppear { Logger.logScreenView(screenName: "ScreenName") }`
- **Objective-C:** `[CAPLogger logScreenViewWithScreenName:@"ScreenName"]`
- Add to **every** screen for complete user journey data

**Verify:** Navigate between screens and confirm `_screen_view` events appear.

### TTI (Time to Interactive)

Record how long the app takes to become interactive after a cold launch.

**$bd-docs:** look up `TTI app launch time interactive`

- Record start time at `Logger.start()` call
- Call `Logger.logAppLaunchTTI(duration)` once when the app becomes interactive
- **Check for SceneDelegate:** If the project uses `SceneDelegate.swift`, use `sceneDidBecomeActive` — `applicationDidBecomeActive` is never called in scene-based apps
- Call exactly once per cold launch

**Verify:** Cold-launch the app and confirm `_app_launch_tti` appears with a plausible duration.

### Structured fields and user identity

Attach metadata to all subsequent logs (user ID, account type, experiment variants).

**$bd-docs:** look up `fields addField`

- `Logger.addField(withKey: "user_id", value: userId)` after login
- On logout or account switch, set updated values (fields are overwritten by key)
- Set any additional fields iwth valuable global metadata using `Logger.addField(withKey: "key", value: value)`
- Field names starting with `_` are reserved

### Spans

Instrument discrete operations with start/end timing (API calls, rendering, checkout flow).

**$bd-docs:** look up `spans startSpan`

- `Logger.startSpan(name:level:fields:)` / `span?.end(.success)`
- Use `defer` to ensure spans are always ended in error paths

### Feature flag exposure

Record which variant a user sees at the moment of divergence.

**$bd-docs:** look up `feature flag exposure`

- Record at the **moment of divergence** — when the flag value affects what the user sees

### dSYM upload

**$bd-docs:** look up `dSYM symbolication debug symbols`

- Configure a build phase script or use `bd debug-files upload` in CI

### App extensions

Not currently supported — do not instrument app extensions with the Capture SDK. Contact the bitdrift team if this is a requirement.

### Analytics event forwarding

Forward existing analytics events to bitdrift at the single submission point:

```swift
var fields: [String: String] = ["analytics_event_name": eventName]
for (key, value) in eventProperties {
    fields["analytics_\(key)"] = "\(value)"
}
Logger.logInfo("analytics_event", fields: fields)
```
