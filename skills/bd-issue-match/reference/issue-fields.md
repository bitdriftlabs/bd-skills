# Issue Report Fields

Field reference for the report object passed to `bdrl_program` in an IssueMatch step.

> **Always verify against the live schema:** `bd schema workflow.create IssueMatch --depth 5`
> The proto definition is authoritative; this file provides interpretation and usage notes.

---

## Known fields

### `.type` — ReportType

Top-level crash category. Use this for coarse filtering before inspecting `.errors[N].name` — it's more reliable than string-matching the reason field.

| Value |
|-------|
| `AppNotResponding` (ANR) |
| `HandledError` |
| `JVMCrash` |
| `MemoryTermination` |
| `NativeCrash` |
| `StrictModeViolation` |
| `JavaScriptNonFatalError` |
| `JavaScriptFatalError` |

```bdrl
# Abort unless this is a native crash
if .type != 5 {
  abort
}

# Branch on crash category
if .type == 5 {
  add_field("category", "native")
} else if .type == 3 {
  add_field("category", "jvm")
} else if .type == 1 {
  add_field("category", "anr")
} else {
  abort
}
```

### `.errors[]`

Array of error objects in the report. Most reports have one error; always guard with `length(.errors) > 0` before indexing.

| Path | Type | Notes |
|---|---|---|
| `.errors[N].name` | string | Fully-qualified exception/signal class name (e.g. `java.lang.NullPointerException`, `SIGABRT`). Preferred field for filtering — use this instead of parsing `.reason`. May be null. |
| `.errors[N].reason` | string | Human-readable error description — the exception message, signal code, or context string. Format varies by platform (see below). May be null. |
| `.errors[N].stack_trace[]` | array | Stack frames, outermost first |
| `.errors[N].stack_trace[M].symbolicated_name` | string | Fully-qualified method or function name. Null if unsymbolicated. |
| `.errors[N].stack_trace[M].source_file.path` | string | Source file path. Null if unsymbolicated or unavailable. |
| `.errors[N].stack_trace[M].source_file.line` | integer | Line number. Null if unsymbolicated. |
| `.errors[N].stack_trace[M].in_app` | boolean | True if this frame is in app/project code (vs system library). |
| `.errors[N].stack_trace[M].frame_type` | integer | Frame kind: 1=JVM, 2=DWARF, 3=AndroidNative, 4=JavaScript |

**Prefer `.name` over parsing `.reason`:** `.name` is the class/signal identifier; `.reason` is the message. For type-based filtering, `.name` is the right field:

```bdrl
if length(.errors) == 0 { abort }
name = string(.errors[0].name) ?? ""
if !contains(name, "NullPointerException") { abort }
```

### `.app_metrics`

Metadata about the app instance that produced the report.

| Path | Type | Notes |
|---|---|---|
| `.app_metrics.app_id` | string | Bundle ID / application ID (e.g. `com.example.myapp`) |
| `.app_metrics.app_version` | string | App version string (e.g. `8.4.1`) |

### `.feature_flags`

**Array** of `{name, value}` objects — **not a keyed map**. Always iterate with `for_each`.

| Path | Type | Notes |
|---|---|---|
| `.feature_flags[N].name` | string | Flag key name |
| `.feature_flags[N].value` | string | Flag value as string |

```bdrl
# CORRECT — iterate the array
for_each(.feature_flags) -> |_i, flag| {
  if flag.name == "my_flag" {
    add_field("my_flag", string(flag.value) ?? "unknown")
  }
}

# WRONG — feature_flags is not a keyed map
.feature_flags.my_flag
```

---

## Platform-specific field values

### `.errors[0].name` — exception class / signal name

| Platform | Example `.name` value |
|---|---|
| Android (Java/Kotlin) | `java.lang.NullPointerException` |
| Android native signal | `SIGABRT`, `SIGSEGV` |
| Android ANR | `ANR`, `Background ANR` |
| iOS (EXC signal) | `EXC_BAD_ACCESS` |
| iOS (NSException) | `NSInvalidArgumentException` |
| React Native (JS) | `TypeError` |

### `.errors[0].reason` — error message / context

| Platform | Example `.reason` value |
|---|---|
| Android (Java/Kotlin) | `Attempt to invoke virtual method 'int...' on a null object reference` |
| Android ANR | `ANR in com.example.myapp` |
| iOS (EXC) | `EXC_BAD_ACCESS (SIGSEGV)` |
| iOS (NSException) | `-[NSNull length]: unrecognized selector sent to instance` |
| iOS (Swift) | `Fatal error: Unexpectedly found nil while unwrapping an Optional value` |
| React Native (JS) | `Cannot read property 'foo' of undefined` |

**Use `.name` for type-based filtering; use `.reason` for message content.** On Android, `.reason` includes the class name as a prefix (`java.lang.NullPointerException: ...`), so you can split on `:` to extract it — but `.name` is cleaner:

```bdrl
# Preferred: use .name directly
name = string(.errors[0].name) ?? ""
if !contains(name, "NullPointerException") { abort }

# Alternative if .name is unavailable: split .reason
reason = string(.errors[0].reason) ?? ""
parts = split(reason, ":")
error_class = parts[0]  # e.g. "java.lang.NullPointerException"
```

---

## Null safety patterns

All fields in `.errors[N].stack_trace[M]` may be null for unsymbolicated reports. Always use coalesce:

```bdrl
name = string(frame.symbolicated_name) ?? ""
path = string(frame.source_file.path) ?? ""
```

Guard array access:

```bdrl
if length(.errors) > 0 {
  # safe to access .errors[0]
  if length(.errors[0].stack_trace) > 1 {
    # safe to access .errors[0].stack_trace[1]
  }
}
```
