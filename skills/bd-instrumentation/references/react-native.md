# React Native Integration

This file provides the workflow and placement guidance. For exact API signatures and code examples, use $bd-docs to look up the relevant topic at each step.

---

## New installation

Only needed when the SDK is not yet in the project. This adds the dependency and gets `init()` running. Once verified, move to the instrumentation categories below.

### Step 1 — Get the SDK key

Ask the user for their bitdrift SDK key (found in the bitdrift portal under Company Settings → SDK Keys). Tell the user you're ready and ask for confirmation before proceeding.

### Step 2 — SDK dependency

Install the npm package and native dependencies.

**$bd-docs:** look up `react native quickstart install`

**Placement tips:**
- `npm install @bitdrift/react-native` (or yarn)
- Run `cd ios && pod install` after installing
- Min iOS 15, Android API 23
- **Important:** The RN SDK is incompatible with `use_frameworks! :linkage => :static` in Podfile (prevents internal Objective-C bridging headers from being generated)

**Verify:** Ask the user to build for both platforms. Confirm it compiles cleanly.

### Step 3 — SDK initialization

Call `init()` as early as possible. Start with a **fixed session strategy** — new session every launch for easy verification.

**$bd-docs:** look up `session strategy configuration init`

**Placement tips:**
- Call `init()` in `App.tsx` or `index.js`, before the app renders
- `import { init, SessionStrategy } from '@bitdrift/react-native'`
- Start with `SessionStrategy.Fixed` for easy verification
- Must initialize on the main process

**Verify:** Ask the user to build and run. Confirm the SDK initializes without errors. The SDK is now installed — present the instrumentation categories below and ask which the user wants to add.

---

## Instrumentation categories

Each category is standalone. Jump directly to whichever one the user needs — whether they just finished a new install or already had the SDK set up. For each, fetch the API details from docs first.

### Log forwarding

Forward existing logging to bitdrift.

- React Native apps typically use `console.log` — there's no built-in log forwarding integration like Timber/CocoaLumberjack
- To forward console logs, wrap `console.log`/`warn`/`error` to also call `info()`/`warning()`/`error()` from `@bitdrift/react-native`
- If the app uses a logging library (e.g., `react-native-logs`), add a bitdrift transport

**Verify:** Build and run, confirm log messages appear in the bitdrift timeline.

### Network monitoring

Add network request instrumentation.

**$bd-docs:** look up `network http instrumentation`

- Check the docs for RN-specific network instrumentation
- If the docs don't cover automatic RN network capture, use the manual HTTP logging API from `sdk/features/http-traffic-logs.md` — wrap `fetch` or use an interceptor library

**Verify:** Trigger a network request and confirm HTTP events appear in the timeline.

### Screen views

Track navigation to power Sankey diagrams, funnels, and user journeys.

**$bd-docs:** look up `screen view automatic instrumentation`

- `import { logScreenView } from '@bitdrift/react-native'`
- **React Navigation:** Use `onStateChange` on `NavigationContainer` to detect screen changes and call `logScreenView(routeName)`
- **Expo Router:** Use the `usePathname()` hook in a layout component
- Add to **every** screen for complete user journey data

**Verify:** Navigate between screens and confirm `_screen_view` events appear.

### TTI (Time to Interactive)

Record how long the app takes to become interactive after a cold launch.

**$bd-docs:** look up `TTI app launch time interactive`

- `import { logAppLaunchTTI } from '@bitdrift/react-native'`
- Record start time at module load, call `logAppLaunchTTI(durationMs)` when the first screen is interactive
- For React Navigation: call in `onReady` callback of `NavigationContainer`
- Call exactly once per cold launch

**Verify:** Cold-launch the app and confirm `_app_launch_tti` appears with a plausible duration.

### Structured fields

Attach metadata to all subsequent logs (user ID, account type, experiment variants).

**$bd-docs:** look up `fields addField`

- `addField("user_id", userId)` after login
- Field names starting with `_` are reserved

### Spans

Instrument discrete operations with start/end timing.

**$bd-docs:** look up `spans startSpan`

- Start/end spans around discrete operations

### Feature flag exposure

Record which variant a user sees at the moment of divergence.

**$bd-docs:** look up `feature flag exposure`

- Record at the **moment of divergence** — when the flag value affects what the user sees

### Crash reporting / session linking

Link bitdrift session context to your crash reporter.

**$bd-docs:** look up `crash fatal issues session linking`

- Pass `getSessionUrl()` to your crash reporter as a custom key

### Analytics event forwarding

Forward existing analytics events to bitdrift at the single submission point:

```typescript
import { info } from '@bitdrift/react-native';

function trackEvent(name: string, props: Record<string, string>) {
  // existing analytics call...
  info("analytics_event", { analytics_event_name: name, ...Object.fromEntries(
    Object.entries(props).map(([k, v]) => [`analytics_${k}`, v])
  )});
}
```
