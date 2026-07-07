# Metrics Recipes

Recipes for emitting chart fields via `add_field` in IssueMatch BDRL scripts, for use with Plot Chart actions.

> Fetch the live function reference before writing — use `$bd-docs` to fetch `product/workflows/scripting/functions.md`.

---

## Cardinality limits

`add_field` values contribute to metric cardinality. Limits:
- **500** distinct tag combinations per metric per aggregation interval (client)
- **1,000** globally per ~30 min rolling window
- **20,000** total dimensions globally

**Use low-cardinality values only:** enum categories, flag names, boolean strings. Never emit user IDs, raw error messages, request paths, or any unbounded string.

---

## Expand a feature flag into a chart dimension

Track crash rate split by feature flag variant:

```bdrl
for_each(.feature_flags) -> |_i, flag| {
  if flag.name == "checkout_v2" {
    add_field("checkout_v2_flag", string(flag.value) ?? "unknown")
  }
}
```

Attach a `Plot Counter Chart` action with **Split by field: checkout_v2_flag**.

See [../reference/workflow-schema.md](../reference/workflow-schema.md) for the `metric_chart_rule` action JSON shape.

---

## Categorize crash type (cross-platform)

Bucket crashes into a small set of category strings:

```bdrl
if length(.errors) > 0 {
  reason = string(.errors[0].reason) ?? ""
  if contains(reason, "NullPointerException") || contains(reason, "null pointer") {
    add_field("error_category", "null_pointer")
  } else if contains(reason, "OutOfMemoryError") {
    add_field("error_category", "oom")
  } else if contains(reason, "ANR") {
    add_field("error_category", "anr")
  } else if contains(reason, "EXC_BAD_ACCESS") {
    add_field("error_category", "bad_access")
  } else if contains(reason, "SIGABRT") {
    add_field("error_category", "sigabrt")
  } else {
    add_field("error_category", "other")
  }
}
```

---

## Emit app version for crash-by-version chart

```bdrl
add_field("crash_app_version", string(.app_metrics.app_version) ?? "unknown")
```

App version is typically low-cardinality enough to use directly. Verify your release cadence — apps releasing many versions per day may hit cardinality limits if this field is combined with other dimensions.

---

## Emit platform type

Useful when a single cross-platform workflow handles both iOS and Android:

```bdrl
if length(.errors) > 0 {
  reason = string(.errors[0].reason) ?? ""
  if contains(reason, "java.lang") || contains(reason, "ANR") || contains(reason, "kotlin") {
    add_field("crash_platform", "android")
  } else if contains(reason, "EXC_") || contains(reason, "NSUI") || contains(reason, "NSInvalid") {
    add_field("crash_platform", "ios")
  } else {
    add_field("crash_platform", "other")
  }
}
```

---

## Foreground vs. background

Split crash volume by whether the app was in the foreground or backgrounded at capture
time, using `.app_metrics.running_state`. See
[../reference/issue-match-fields.md](../reference/issue-match-fields.md#app_metricsrunning_state--foregroundbackground-state)
for why there's no single literal meaning "background" on Android — this pattern derives it
as "anything that is not exactly `foreground`":

```bdrl
state = string(.app_metrics.running_state) ?? ""
is_foreground = state == "foreground"
app_state = if is_foreground { "foreground" } else { "background" }
add_field("app_state", app_state)
```

Attach a `Plot Counter Chart` action with **Split by field: app_state** to see both as
series on one chart. If you'd rather have them as fully independent workflows/charts/alerts
instead of one chart with two series, use two separate `IssueMatch` steps — one that
`abort`s unless `is_foreground`, one that `abort`s when `is_foreground` — each with its own
`metric_chart_rule` action.

---

## Emit a custom field value

Pull a value from `.fields` (custom fields set via `Logger.addField()`) into a chart
dimension. Values are typed as "any," so always type-check before use:

```bdrl
value = .fields.prod_category
if is_string(value) {
  add_field("category", string(value) ?? "unknown")
} else {
  abort
}
```

For a list of possible keys rather than one fixed key, use `get()` instead of hardcoding a
lookup per key:

```bdrl
my_fields = ["prod_category", "option_split"]

for_each(my_fields) -> |_index, key| {
  value, err = get(.fields, [key])
  if err == null && is_string(value) {
    add_field(key, string(value) ?? "unknown")
  }
}
```

---

## Search all stack frames across all errors

`.errors[0].stack_trace` only looks at the top-level error's frames. To check **every**
error's frames — e.g. "does this crash involve library X anywhere in the stack, not just the
top frame" — use `any`/`map`/`filter`/`flatten` instead of indexing:

```bdrl
# true/false: does any frame in any error match an exact symbol name?
has_library_x = any(.errors) -> |_i, error| {
  any(error.stack_trace) -> |_j, frame| {
    is_string(frame.symbolicated_name) && frame.symbolicated_name == "LibraryX.someFunction"
  }
}

add_field("has_library_x", to_string(has_library_x))
```

```bdrl
# collect every frame across every error that mentions a module, then use the first match
matching_frames = flatten(map(.errors) -> |_i, error| {
  filter(error.stack_trace) -> |_j, frame| {
    is_string(frame.symbolicated_name) && contains(frame.symbolicated_name, "MyModule")
  }
})

if length(matching_frames) > 0 {
  add_field("owning_module_frame", matching_frames[0].symbolicated_name)
} else {
  abort
}
```

`map()` over `.errors` produces an array of arrays (one array of matching frames per error) —
`flatten()` collapses that into a single flat array before you index into it.

---

## Wiring into the workflow

Attach a `metric_chart_rule` action to the IssueMatch step. The `add_field` names become available as `group_by` dimensions:

```json
{
  "rule_id": "crash-by-category",
  "metric_chart_rule": {
    "time_series": [{
      "count": {
        "value": { "match_id": "issue-step" },
        "group_by": { "values": [{ "field_key": "error_category" }] }
      }
    }]
  }
}
```

See [../reference/workflow-schema.md](../reference/workflow-schema.md) for full action shapes.

---

## Pitfalls

| Mistake | Fix |
|---|---|
| `add_field` value is a raw error message or user ID | Bucket into a small set of enum strings first |
| Emitting all feature flags as separate field names | Unknown flag count → cardinality explosion; iterate and emit only known flags |
| No `Plot Chart` action attached | `add_field` emissions are invisible without a downstream chart action |
| Using `abort` then `add_field` later | `abort` discards all modifications including prior `add_field` calls |
