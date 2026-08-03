# Metrics Recipes

Recipes for emitting chart fields via `add_field` in IssueMatch Ripsaw scripts, for use with Plot Chart actions.

> Fetch the live function reference before writing — use `$bd-docs` to fetch `product/workflows/scripting/functions.md`, and `product/workflows/scripting/structures.md` for report field names.

---

## Cardinality limits

`add_field` values contribute to metric cardinality. Limits:
- **500** distinct tag combinations per metric per aggregation interval (client)
- **1,000** globally per ~30 min rolling window
- **20,000** total dimensions globally

**Use low-cardinality values only:** enum categories, flag names, boolean strings. Never emit user IDs, raw error messages, request paths, or any unbounded string.

### Overflow shows up as an `other` bucket, not as an error

When a dimension exceeds its cardinality budget, the excess values are folded into a series
literally labelled `other` — no error, no warning. A chart of symbolicated frame names collected
`other` as its single largest series while the individually-named frames each held a handful of
events, which reads as "most crashes come from `other`" rather than "this dimension overflowed".

Check `cardinality_overflows` in the chart JSON to tell the two apart:

```bash
bd workflow charts <id> -o json --jq '[.data[] | select(.error == null) | .line_data.time_series[]? | .cardinality_overflows]'
```

If you see an `other` series on a dimension you know to be high-cardinality, narrow the workflow
(filter to one crash type, one module) rather than charting it across everything.

## Don't collide with built-in dimension names

`add_field("platform", ...)` is silently overwritten by the metric system's own `platform` tag: two
workflows emitting the identical expression `string(.device_metrics.platform) ?? "MISSING"` chart as
`Android` under the name `p_platform` but as `android` under the name `platform`. Prefix your
dimension names (`crash_platform`, `app_platform`) rather than reusing names the platform already
attaches to every metric.

---

## Expand a feature flag into a chart dimension

Track crash rate split by feature flag variant. `.feature_flags[N].value` is already a string, so it can be passed straight to `add_field`:

```ripsaw
for_each(.feature_flags) -> |_i, flag| {
  if flag.name == "checkout_v2" {
    add_field("checkout_v2_flag", flag.value)
  }
}
```

Note the asymmetry: iterating `.feature_flags` **directly** gives typed `flag.name` / `flag.value`,
so coercing them raises E651. Iterating the result of `filter()` gives `any` and *requires*
coercion — see [issue-match-examples.md #7](issue-match-examples.md#7-feature-flag-expansion) for
the filter-a-known-set version, which also aborts when no flag matches so unrelated reports don't
emit a metric.

Attach a `Plot Counter Chart` action with **Split by field: checkout_v2_flag**.

See [../reference/workflow-schema.md](../reference/workflow-schema.md) for the `metric_chart_rule` action JSON shape.

---

## Categorize crash type (cross-platform)

Branch on `.type` first — it's a stable enum — and only fall back to reason matching for finer buckets:

```ripsaw
if .type == "AppNotResponding" {
  add_field("error_category", "anr")
} else if .type == "MemoryTermination" {
  add_field("error_category", "oom")
} else if length(.errors) > 0 {
  name = string(.errors[0].name) ?? ""
  reason = string(.errors[0].reason) ?? ""
  if contains(name, "NullPointerException") || contains(reason, "null object reference") {
    add_field("error_category", "null_pointer")
  } else if contains(name, "OutOfMemoryError") {
    add_field("error_category", "oom")
  } else if contains(name, "EXC_BAD_ACCESS") {
    add_field("error_category", "bad_access")
  } else if contains(name, "SIGABRT") {
    add_field("error_category", "sigabrt")
  } else {
    add_field("error_category", "other")
  }
} else {
  add_field("error_category", "other")
}
```

To split ANRs further by the dispatch-timeout detail in the reason text, see
[issue-match-examples.md #10](issue-match-examples.md#10-anr-classification).

---

## Emit app version for crash-by-version chart

```ripsaw
add_field("crash_app_version", string(.app_metrics.version) ?? "unknown")
```

The field is `.app_metrics.version`, not `app_version`.

App version is typically low-cardinality enough to use directly. Verify your release cadence — apps releasing many versions per day may hit cardinality limits if this field is combined with other dimensions.

---

## Emit platform type

Useful when a single cross-platform workflow handles both iOS and Android.
`.device_metrics.platform` is a real enum field (`Android`, `iOS`, `macOS`, `Unknown`) — use it
instead of guessing from error strings. Script:
[issue-match-examples.md #5](issue-match-examples.md#5-platform-split). Don't name the dimension
`platform` — see the built-in name collision above.

---

## Foreground vs. background

Split crash volume by whether the app was in the foreground or backgrounded at capture time, using
`.app_metrics.running_state`. Script:
[issue-match-examples.md #6](issue-match-examples.md#6-foreground-vs-background). See
[../reference/issue-match-fields.md](../reference/issue-match-fields.md#app_metricsrunning_state--foregroundbackground-state)
for why there's no single literal meaning "background" on Android.

**Emit the raw value alongside the derived bucket.** Because the bucket is derived as "anything
that is not `foreground`", a report where the field isn't populated charts as `background` —
indistinguishable from a genuine background crash unless the raw field is charted too.

Attach a `Plot Counter Chart` action with **Split by field: app_state** to see both as
series on one chart. If you'd rather have them as fully independent workflows/charts/alerts
instead of one chart with two series, use two separate `IssueMatch` steps — one that
`abort`s unless `is_foreground`, one that `abort`s when `is_foreground` — each with its own
`metric_chart_rule` action.

---

## Emit a custom field value

Pull a value from `.fields` (custom fields set via `Logger.addField()`) into a chart
dimension. Values are typed as "any," so always type-check before use:

```ripsaw
value = .fields.prod_category
if is_string(value) {
  add_field("category", to_string(value))
} else {
  abort
}
```

For a list of possible keys rather than one fixed key, use `get()` instead of hardcoding a lookup
per key — see [issue-match-examples.md #8](issue-match-examples.md#8-custom-fields-by-key-list).
`get()` returns `any` and `is_string()` does not narrow it, so the value needs coercing inside
`add_field` (bare `value` → E110, `to_string(value)` → E630).

---

## Search all stack frames across all errors

`.errors[0].stack_trace` only looks at the top-level error's frames. To check **every**
error's frames — e.g. "does this crash involve library X anywhere in the stack, not just the
top frame" — use `any`/`map`/`filter`/`flatten` instead of indexing:

```ripsaw
# true/false: does any frame in any error match an exact symbol name?
has_library_x = any(.errors) -> |_i, error| {
  any(error.stack_trace) -> |_j, frame| {
    frame.symbolicated_name == "LibraryX.someFunction"
  }
}

add_field("has_library_x", to_string(has_library_x))
```

```ripsaw
# collect every frame across every error that mentions a module, then use the first match
matching_frames = flatten(map(.errors) -> |_i, error| {
  filter(error.stack_trace) -> |_j, frame| {
    is_string(frame.symbolicated_name) && contains(frame.symbolicated_name, "MyModule")
  }
})

if length(matching_frames) > 0 {
  add_field("owning_frame", string(matching_frames[0].symbolicated_name) ?? "unknown")
} else {
  abort
}
```

`map()` over `.errors` produces an array of arrays (one array of matching frames per error) —
`flatten()` collapses that into a single flat array before you index into it.

Restrict to app code by checking `frame.in_app`, or to a symbolication state with
`frame.frame_status == "Symbolicated"` — both are real Frame fields.

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
| `contains(my_array, item)` | `contains` is string-only; use `includes(my_array, item)` for arrays |
| `.app_metrics.app_version` | The field is `.app_metrics.version` |
| Comparing `frame.type` / `frame.frame_status` to integers | Both are string enums (`"JVM"`, `"Symbolicated"`) |
