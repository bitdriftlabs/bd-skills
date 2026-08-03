# Issue Report Fields

Field reference for the `Report` object passed to the Ripsaw `program` in an IssueMatch step.

> **Authoritative sources — check both:**
> - Structure definitions: `$bd-docs` → `product/workflows/scripting/structures.md` (the `Report` type and everything it nests)
> - Live request shape: `bd schema workflow.create IssueMatch --depth 5`
>
> This file provides interpretation and usage notes on top of those.

---

## Report — top level

| Path | Type | Notes |
|---|---|---|
| `.type` | ReportType (string enum) | Crash category. Best first filter — see below. |
| `.errors` | array of Error | First entry is the captured error; later entries are related (e.g. cause chain). |
| `.app_metrics` | AppMetrics | App build + process state at capture time. |
| `.device_metrics` | DeviceMetrics | Device model, OS, power, network, thermal state. |
| `.feature_flags` | array of FeatureFlag | Array, **not** a keyed map. |
| `.fields` | map of string → any | Custom/global fields present on the report. |
| `.sdk` | SDKInfo | `.sdk.id`, `.sdk.version` — Capture SDK build that produced the report. |
| `.thread_details` | ThreadDetails | `.thread_details.count`, `.thread_details.threads[]`. No guaranteed thread ordering. |
| `.binary_images` | array of BinaryImage | `.id`, `.path`, `.load_address` — images referenced by stack frames. |

---

## `.type` — ReportType

Top-level crash category. Use this for coarse filtering before inspecting `.errors[N].name` — it's more reliable than string-matching the reason field.

| Value |
|-------|
| `Unknown` |
| `AppNotResponding` (ANR) |
| `HandledError` |
| `JVMCrash` |
| `MemoryTermination` |
| `NativeCrash` |
| `StrictModeViolation` |
| `JavaScriptNonFatalError` |
| `JavaScriptFatalError` |

```ripsaw
# Abort unless this is a native crash
if .type != "NativeCrash" {
  abort
}

# Branch on crash category
if .type == "NativeCrash" {
  add_field("category", "native")
} else if .type == "JVMCrash" {
  add_field("category", "jvm")
} else if .type == "AppNotResponding" {
  add_field("category", "anr")
} else {
  abort
}
```

---

## `.errors[]`

Array of error objects in the report. Most reports have one error; always guard with `length(.errors) > 0` before indexing.

| Path | Type | Notes |
|---|---|---|
| `.errors[N].name` | string | Descriptive category — fully-qualified exception name, Mach/POSIX signal, or termination category (e.g. `java.lang.NullPointerException`, `SIGABRT`, `Application Not Responding`). Preferred field for filtering over parsing `.reason`. May be null. |
| `.errors[N].reason` | string | Contextual message — usually the exception message. Format varies by platform (see below). May be null. |
| `.errors[N].stack_trace[]` | array of Frame | Frames ordered most-recently-executed first (`main()` is last, not first). |
| `.errors[N].relation_to_next` | string enum | How this error relates to the next entry in `.errors`. Currently only `CausedBy`. |

### Frame fields — `.errors[N].stack_trace[M]`

| Path | Type | Notes |
|---|---|---|
| `.symbolicated_name` | string | Symbolicated function name. Null if unsymbolicated. The field most scripts match on. |
| `.symbol_name` | string | Raw method/function name as reported on device (pre-symbolication). |
| `.class_name` | string | Fully-qualified class name, if any. |
| `.in_app` | boolean | True if the frame is app/project code rather than a system library. |
| `.source_file.path` | string | Source file path. Null if unavailable. |
| `.source_file.line` | integer | Line number. |
| `.source_file.column` | integer | Column number. |
| `.type` | string enum | Frame kind: `Unknown`, `JVM`, `DWARF`, `AndroidNative`, `JavaScript`. |
| `.frame_status` | string enum | Symbolication result: `Missing`, `Symbolicated`, `MissingSymbol`, `UnknownImage`, `Malformed`. |
| `.image_id` | string | Binary/JS bundle identifier — corresponds to `.binary_images[N].id`. |
| `.frame_address` / `.symbol_address` | integer | Addresses, for native frames. |
| `.original_index` | integer | Frame index before symbolication (symbolication can expand one frame into several). |
| `.state` | array of string | Platform-specific thread context, e.g. blocked-on-lock information. |
| `.js_bundle_path` | string | (React Native / JS) Full bundle or module URL. |

Frame kind and symbolication status are **string enums**, not integers. Iterate `.errors` with
`map`/`filter` rather than indexing `.errors[0]` — indexed access resolves to `undefined or T`,
which makes every downstream call fallible:

```ripsaw
# only symbolicated in-app JVM frames, across every error
frames = flatten(map(.errors) -> |_i, error| {
  filter(error.stack_trace) -> |_j, frame| {
    frame.type == "JVM" && frame.frame_status == "Symbolicated" && frame.in_app == true
  }
})
add_field("jvm_in_app_frames", to_string(length(frames)))
```

**Prefer `.name` over parsing `.reason`:** `.name` is the class/signal identifier; `.reason` is the message. For type-based filtering, `.name` is the right field:

```ripsaw
if length(.errors) == 0 { abort }
name = string(.errors[0].name) ?? ""
if !contains(name, "NullPointerException") { abort }
```

---

## `.app_metrics`

Metadata about the app instance that produced the report.

| Path | Type | Notes |
|---|---|---|
| `.app_metrics.app_id` | string | Bundle ID / application ID (e.g. `com.example.myapp`). `BuildConfig.APPLICATION_ID` / `CFBundleIdentifier`. |
| `.app_metrics.version` | string | Installed app version (e.g. `8.4.1`). `BuildConfig.VERSION_NAME` / `CFBundleShortVersionString`. **Not `app_version`.** |
| `.app_metrics.build_number.version_code` | integer | (Android) version code. |
| `.app_metrics.build_number.cf_bundle_version` | string | (Apple) `CFBundleVersion`. |
| `.app_metrics.running_state` | string | Foreground/background state at capture time. Platform-specific values — see below. May be null. |
| `.app_metrics.process_id` | integer | PID of the running process. |
| `.app_metrics.region_format` | string | Installed regional variant of the app. |
| `.app_metrics.memory.total` / `.free` / `.used` | integer | Memory state at capture time. |
| `.app_metrics.cpu_usage.used_percent` | integer | App CPU usage, 0–100. |
| `.app_metrics.cpu_usage.duration_seconds` | integer | Seconds elapsed while active. |
| `.app_metrics.lifecycle_event` | string | (Apple) lifecycle hook running before termination — `process-launch`, `scene-create`, etc. |
| `.app_metrics.javascript_engine` | string enum | (React Native / JS) `UnknownEngine`, `JavaScriptCore`, `Hermes`. |

---

## `.device_metrics`

| Path | Type | Notes |
|---|---|---|
| `.device_metrics.platform` | string enum | `Unknown`, `Android`, `iOS`, `macOS`. The reliable way to branch on platform — don't infer it from error strings. |
| `.device_metrics.manufacturer` / `.model` | string | Device manufacturer and model. |
| `.device_metrics.os_build.version` | string | OS version. Android also has `.brand` and `.fingerprint`; Apple also has `.kern_osversion`. |
| `.device_metrics.arch` | string enum | `Unknown`, `arm32`, `arm64`, `x86`, `x86_64`. |
| `.device_metrics.network_state` | string enum | `Unknown`, `Disconnected`, `Cellular`, `WiFi`. |
| `.device_metrics.power_metrics.power_state` | string enum | `Unknown`, `RunningOnBattery`, `PluggedInNoBattery`, `PluggedInCharging`, `PluggedInCharged`. |
| `.device_metrics.power_metrics.charge_percent` | integer | 0–100. |
| `.device_metrics.low_power_mode_enabled` | boolean | Reduced power consumption mode. |
| `.device_metrics.thermal_state` | integer | Platform-specific constants: Android maps `THERMAL_STATUS_*` to 1–6; iOS maps `NSProcessInfoThermalState` to 0–4. |
| `.device_metrics.rotation` | string enum | `Unknown`, `Portrait`, `LandscapeRight`, `LandscapeLeft`, `PortraitUpsideDown`. |
| `.device_metrics.display.height` / `.width` / `.density_dpi` | integer | Display geometry. |
| `.device_metrics.cpu_usage.used_percent` | integer | Total device CPU usage. |
| `.device_metrics.cpu_abis` | array of string | (Android) supported ABIs, in preference order. |
| `.device_metrics.time` | Timestamp | `.seconds` and `.nanos` — the moment the event occurred. |
| `.device_metrics.timezone` | string | Timezone of `.time`. |

Platform is a first-class field — prefer it over reason-string heuristics:

```ripsaw
add_field("crash_platform", string(.device_metrics.platform) ?? "unknown")
```

---

## `.feature_flags`

**Array** of `{name, value, timestamp}` objects — **not a keyed map**. Always iterate with `for_each`.

| Path | Type | Notes |
|---|---|---|
| `.feature_flags[N].name` | string | Flag key name |
| `.feature_flags[N].value` | string | Flag value as string |
| `.feature_flags[N].timestamp` | Timestamp | When the flag was last modified |

```ripsaw
# CORRECT — iterate the array
for_each(.feature_flags) -> |_i, flag| {
  if flag.name == "my_flag" {
    add_field("my_flag", flag.value)
  }
}

# WRONG — feature_flags is not a keyed map
.feature_flags.my_flag
```

---

## `.fields`

Map of custom/global field key-values present on the report (e.g. fields set via
`Logger.addField()`). Unlike `.feature_flags`, this **is** a keyed map, so direct path access
works — but values are typed as "any," so check the type before use.

| Path | Type | Notes |
|---|---|---|
| `.fields.<key>` | any | Custom field value. May be absent or a non-string type — always type-check. |

```ripsaw
# fixed key
value = .fields.prod_category
if is_string(value) {
  add_field("category", to_string(value))
} else {
  abort
}
```

```ripsaw
# list of possible keys — use get() instead of hardcoding each one
my_fields = ["prod_category", "option_split"]

for_each(my_fields) -> |_index, key| {
  value, err = get(.fields, [key])
  if err == null && is_string(value) {
    add_field(key, string(value) ?? "unknown")
  }
}
```

`get()` returns `any`, and an `is_string()` guard does **not** narrow the type for the compiler —
`add_field(key, value)` fails with E110 and `add_field(key, to_string(value))` fails with E630.
Coerce explicitly inside the call, as above.

---

## `.thread_details`

| Path | Type | Notes |
|---|---|---|
| `.thread_details.count` | integer | Total thread count — may exceed the number captured in `.threads`. |
| `.thread_details.threads[N].name` | string | Thread name, if any. |
| `.thread_details.threads[N].active` | boolean | True for the thread reporting the problem. |
| `.thread_details.threads[N].index` | integer | Numeric thread identifier. |
| `.thread_details.threads[N].state` | string | Platform-specific operation mode. |
| `.thread_details.threads[N].priority` | float | Apple: 0.0–1.0. Android: 1–10. |
| `.thread_details.threads[N].quality_of_service` | integer | (Apple) `QualityOfService` level. |
| `.thread_details.threads[N].stack_trace[]` | array of Frame | Same Frame shape as `.errors[N].stack_trace`. |
| `.thread_details.threads[N].summary` | string | Highlight of the most important thread data. |

**Compiler caveat:** `.thread_details` is not in the script compiler's static schema — it resolves
to `undefined`, exactly like a misspelled path, so `filter(.thread_details.threads)` is rejected
with E110. Coerce first if you need it, and verify against a real report before relying on it:

```ripsaw
threads = array(.thread_details.threads) ?? []
active = filter(threads) -> |_i, thread| {
  thread.active == true
}
add_field("active_threads", to_string(length(active)))
```

The same applies to `.app_metrics`, `.device_metrics`, and `.sdk` — see "Statically typed vs
dynamic paths" below.

---

## Platform-specific field values

### `.errors[0].name` — exception class / signal name

| Platform | Example `.name` value |
|---|---|
| Android (Java/Kotlin) | `java.lang.NullPointerException` |
| Android native signal | `SIGABRT`, `SIGSEGV` |
| iOS (EXC signal) | `EXC_BAD_ACCESS` |
| iOS (NSException) | `NSInvalidArgumentException` |
| React Native (JS) | `TypeError` |
| Termination categories | `Application Not Responding`, `Memory Pressure Termination`, `StrictMode Violation` |

For ANR and memory terminations, prefer `.type == "AppNotResponding"` / `"MemoryTermination"` over
matching `.name` strings — the enum is stable, the human-readable name is not.

### `.errors[0].reason` — error message / context

| Platform | Example `.reason` value |
|---|---|
| Android (Java/Kotlin) | `Attempt to invoke virtual method 'int...' on a null object reference` |
| Android ANR | `Input dispatching timed out ...` |
| iOS (EXC) | `EXC_BAD_ACCESS (SIGSEGV)` |
| iOS (NSException) | `-[NSNull length]: unrecognized selector sent to instance` |
| iOS (Swift) | `Fatal error: Unexpectedly found nil while unwrapping an Optional value` |
| React Native (JS) | `Cannot read property 'foo' of undefined` |

**Use `.name` for type-based filtering; use `.reason` for message content.** On Android, `.reason` includes the class name as a prefix (`java.lang.NullPointerException: ...`), so you can split on `:` to extract it — but `.name` is cleaner:

```ripsaw
# .name is cleanest; splitting .reason is the fallback
if length(.errors) == 0 {
  abort
}
name = string(.errors[0].name) ?? ""
if name != "" {
  add_field("error_class", name)
} else {
  reason = string(.errors[0].reason) ?? ""
  parts = split(reason, ":")
  add_field("error_class", string(parts[0]) ?? "unknown")
}
```

### `.app_metrics.running_state` — foreground/background state

| Platform | Values |
|---|---|
| Android | `foreground`, `foreground_service`, `perceptible`, `cached` |
| Apple | `active`, `inactive`, `background` |

`cached` was observed live on Android but is absent from the documented value list — treat that
list as incomplete and chart the raw value before hardcoding comparisons against it.

**Android has no literal `"background"` value.** There is no single enum value meaning
"backgrounded" on Android — define it as "anything that is not exactly `foreground`":

```ripsaw
state = string(.app_metrics.running_state) ?? ""
is_foreground = state == "foreground"
if !is_foreground {
  abort  # keeps only foreground reports; invert to !is_foreground to keep background instead
}
```

Apple platforms do have a dedicated `"background"` value, so `state == "background"` works
directly there — but a script meant to run cross-platform should still use the
`!= "foreground"` form so it behaves correctly on Android too.

---

## Null safety patterns

Fields in `.errors[N].stack_trace[M]` may be null for unsymbolicated reports, but **whether you
coalesce depends on how you reached them**, not on whether they can be null.

Frames reached by iterating `.errors` are statically typed, so guarding them is itself a compile
error (E651, "this expression can't fail") — use them bare and let `is_string()` filter the nulls:

```ripsaw
named = flatten(map(.errors) -> |_i, error| {
  filter(error.stack_trace) -> |_j, frame| {
    is_string(frame.symbolicated_name)
  }
})
add_field("named_frames", to_string(length(named)))
```

Coalescing is required in the opposite case — untyped paths (`.app_metrics.*`,
`.device_metrics.*`, `.sdk.*`) and anything out of `get()` or `filter()`:

```ripsaw
add_field("app_id", string(.app_metrics.app_id) ?? "unknown")
```

`to_string()` is the alternative when you want null coerced to `""` rather than a custom fallback —
`to_string(null)` returns the empty string. It is fallible only for arrays and objects.

Guard array access. Note that `.errors[0]` resolves to `undefined or T`, so calls over it are
fallible even inside a `length(.errors) > 0` guard — the guard doesn't narrow the type:

```ripsaw
if length(.errors) > 0 {
  n = length(.errors[0].stack_trace) ?? 0
  bucket = if n > 20 { "deep" } else { "shallow" }
  add_field("stack_depth", bucket)
} else {
  abort
}
```

---

## Statically typed vs dynamic paths

The script compiler carries a static schema for only part of the `Report`. This determines which
paths you can pass directly to `length()`, `filter()`, `for_each()`, and `add_field()`, and which
need coercion first.

| Path | Compiler sees | Consequence |
|---|---|---|
| `.type` | string | Can be passed to `add_field` bare. |
| `.errors`, `.feature_flags`, `.fields`, `.binary_images` | array / object | Can be iterated directly. Fields reached through a closure (e.g. `flag.value`, `frame.symbolicated_name`) are typed, so coercing them raises E651. |
| `.errors[N]`, `.errors[N].stack_trace` | `undefined or T` | Calls over them are fallible — add `?? default` or `!`. |
| `.app_metrics.*`, `.device_metrics.*`, `.sdk.*`, `.thread_details.*` | `undefined` | Same as a misspelled path at compile time. Must be coerced (`string(...) ?? "fallback"`) before use; can't be passed to `length()`/`filter()` without `array(...) ?? []`. |

**Being invisible to the compiler does not mean absent at runtime.** `.app_metrics.version`,
`.device_metrics.platform`, and `.sdk.version` all return real values on uploaded reports — the
compiler simply doesn't type them.

The real hazard is the flip side: because unknown paths and misspelled paths compile identically,
**a typo in `.app_metrics.*` or `.device_metrics.*` will not fail to compile** — it silently
produces your fallback at runtime. `.app_metrics.app_version` (the name this reference previously
used) compiles cleanly and charts as the fallback on every report; the correct field is
`.app_metrics.version`.

So when you first use one of these paths, give it a distinctive fallback (`"MISSING"`), chart it,
and confirm real values come back before building on it.

**Availability varies by report type**, so check against the report type you actually care about.
Charting these across Android `JVMCrash`, `NativeCrash`, and `AppNotResponding` reports:

| Path | Availability |
|---|---|
| `.app_metrics.version` | every report type |
| `.app_metrics.build_number.version_code` | every report type |
| `.device_metrics.platform` | every report type |
| `.device_metrics.os_build.version` | every report type |
| `.app_metrics.process_id` | some reports; `0` on others |
| `.app_metrics.running_state` | some reports; fallback on others |
| `.device_metrics.model` | some reports; fallback on most |
| `.sdk.version` | crash reports; fallback on `AppNotResponding` |
| `.app_metrics.memory.*` | never populated |
| `.app_metrics.app_version` | never — the field does not exist |

Treat this as a starting point, not a contract — it reflects one Android SDK version. Run the
`MISSING`-fallback check above for the fields and report types your workflow depends on.
