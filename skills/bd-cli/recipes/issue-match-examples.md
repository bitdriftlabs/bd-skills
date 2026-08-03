# IssueMatch: tested example programs

Ten complete Ripsaw programs for IssueMatch steps. Every one was compiled by the live workflow
service (`bd workflow create` rejects a bad program with the full compiler diagnostic) and deployed
against a real Android app.

Use these as starting points rather than writing from scratch — the compiler rules in
[issue-match.md](issue-match.md#compiler-rules-that-reject-otherwise-reasonable-scripts) reject a
lot of otherwise-reasonable code, and these are known-good shapes.

Each example lists the `add_field` names it emits. Those names must appear in the chart action's
`group_by.values[].field_key`, or the values never surface.

Values shown as "live values" were observed on real uploaded Android reports.

---

## 1. Crash type breakdown

Bucket every uploaded report by its `ReportType`. The simplest useful script — `.type` is one of
the few paths the compiler types as a string, so it needs no coercion.

```ripsaw
add_field("crash_type", .type)
```

Emits: `crash_type`. Live values observed: `JVMCrash`, `NativeCrash`, `AppNotResponding`. Full
enum: those three plus `MemoryTermination`, `HandledError`, `StrictModeViolation`,
`JavaScriptFatalError`, `JavaScriptNonFatalError`, `Unknown`.

---

## 2. Native signal breakdown

Native crashes only, split by signal. Reports that aren't native crashes are dropped, so the step
count is a clean native-crash counter.

```ripsaw
if .type != "NativeCrash" {
  abort
}
if length(.errors) == 0 {
  abort
}
add_field("signal", string(.errors[0].name) ?? "unknown")
```

Emits: `signal`. Live values: `SIGSEGV`, `SIGABRT`, `SIGBUS`, `SIGFPE`.

---

## 3. Exception class, with a fallback

`.name` is the exception class; when it's absent, the class is the prefix of `.reason` before the
first colon on Android.

```ripsaw
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

Emits: `error_class`. Live values: `java.lang.IllegalStateException`,
`java.lang.ArithmeticException`, `java.lang.ArrayIndexOutOfBoundsException`,
`java.lang.AssertionError`, `java.lang.OutOfMemoryError`.

---

## 4. Crash volume by app version

Note the array literal — two `add_field` calls as consecutive statements are rejected with E900.

```ripsaw
[
  add_field("app_version", string(.app_metrics.version) ?? "MISSING"),
  add_field("build", string(.app_metrics.build_number.version_code) ?? "MISSING")
]
```

Emits: `app_version`, `build`.

The field is `.app_metrics.version` — **not** `app_version`. `.app_metrics.*` is invisible to the
compiler, so the wrong name compiles cleanly and charts as the fallback on every report. Deploy
with a distinctive fallback like `MISSING` the first time and confirm real values come back before
trusting a field name.

---

## 5. Platform split

`.device_metrics.platform` is a real enum — more reliable than inferring platform from error text.

```ripsaw
add_field("crash_platform", string(.device_metrics.platform) ?? "MISSING")
```

Emits: `crash_platform`. Values: `Android`, `iOS`, `macOS`, `Unknown`.

Do **not** name this field `platform`. The metric system attaches its own `platform` tag, and it
wins: the identical script charted as `Android` under the name `p_platform` but as `android` under
the name `platform`.

---

## 6. Foreground vs background

Android has no literal `background` value, so derive it as "not exactly `foreground`". The raw
value is emitted alongside the bucket so the underlying enum stays visible.

```ripsaw
state = string(.app_metrics.running_state) ?? "MISSING"
bucket = if state == "foreground" { "foreground" } else { "background" }
[
  add_field("app_state", bucket),
  add_field("running_state_raw", state)
]
```

Emits: `app_state`, `running_state_raw`.

The `if` must be assigned to `bucket` first — passing it inline as an `add_field` argument is a
syntax error.

**Check `running_state_raw` before trusting `app_state`.** Live values observed: `foreground`,
`cached`, and the fallback — availability varies by report type. The "not exactly foreground" rule
turns an unpopulated field into a confident-looking `background`, so the raw field is what tells
you which reports actually carried the value. `cached` is not in the documented value list.

---

## 7. Feature flag expansion

Emit a known set of flags as chart dimensions and drop reports carrying none of them.

```ripsaw
my_flags = ["checkout_v2", "new_cart"]

matching = filter(.feature_flags) -> |_index, flag| {
  includes(my_flags, flag.name)
}

if length(matching) == 0 {
  abort
}

for_each(matching) -> |_index, flag| {
  add_field(string(flag.name) ?? "flag", string(flag.value) ?? "unknown")
}
```

Emits: one field per matched flag name.

Two traps here: `includes()` is the array membership function (`contains()` is string-only and
fails with E110), and values pulled off a `filter()` result are `any`, so they need coercion —
even though the same fields are typed when you iterate `.feature_flags` directly.

---

## 8. Custom fields by key list

Pull several custom field keys without hardcoding a lookup per key.

```ripsaw
my_fields = ["screen_name", "app_state"]

for_each(my_fields) -> |_index, key| {
  value, err = get(.fields, [key])
  if err == null && is_string(value) {
    add_field(key, string(value) ?? "unknown")
  }
}
```

Emits: one field per key present on the report.

The `is_string()` guard does not narrow the type — `add_field(key, value)` fails with E110 and
`add_field(key, to_string(value))` fails with E630. The `string(value) ?? "unknown"` form is the
one that compiles.

---

## 9. Attribute a crash to the owning code

Find the first in-app frame across every error in the report — not just `.errors[0]` — and use it
as an ownership dimension.

```ripsaw
in_app_frames = flatten(map(.errors) -> |_i, error| {
  filter(error.stack_trace) -> |_j, frame| {
    frame.in_app == true && is_string(frame.symbolicated_name)
  }
})

if length(in_app_frames) == 0 {
  abort
}

add_field("owning_frame", string(in_app_frames[0].symbolicated_name) ?? "unknown")
```

Emits: `owning_frame` — e.g. `com.example.checkout.CartActivity.submit`.

Watch cardinality: symbolicated frame names are high-cardinality. Deployed across all crash types,
this chart's largest series was the overflow bucket `other` — the named frames each held only a
few events. Prefer this on a filtered subset (one crash type, one module) rather than across all
crashes.

`map` over `.errors` returns an array per error, so `flatten` is required before indexing.
Iterating `.errors` this way also keeps frames statically typed — `filter(.errors[0].stack_trace)`
is rejected with E121.

---

## 10. ANR classification

Split ANRs by whether the main thread was blocked on input dispatch.

```ripsaw
if .type != "AppNotResponding" {
  abort
}
raw, err = get(.errors, [0, "reason"])
reason = to_string(raw) ?? ""
if err == null && contains(reason, "Input dispatching timed out") {
  add_field("anr_kind", "slow_ui")
} else {
  add_field("anr_kind", "other")
}
```

Emits: `anr_kind`. Verified against live `AppNotResponding` reports, which charted as `slow_ui`.

The predicate has to stay on one line — breaking before `&&` is a syntax error — and `reason` has
to be coerced into a real string before `contains()` will accept it.

---

## Deploying one of these

```bash
bd workflow create workflow.json --metadata-file metadata.json   # compiles the script
bd workflow deploy <id>                                          # starts evaluating reports
bd workflow charts <id> -o json                                  # read the emitted dimensions
```

See [issue-match.md](issue-match.md) for the full workflow JSON wrapper and the compiler rules, and
[issue-match-metrics.md](issue-match-metrics.md) for cardinality limits and chart wiring.
