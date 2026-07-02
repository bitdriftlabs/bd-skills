# Metrics Recipes

Recipes for emitting chart fields via `add_field` in IssueMatch BDRL scripts, for use with Plot Chart actions.

> Fetch the live function reference before writing: `curl -sL https://docs.bitdrift.io/product/workflows/scripting/functions.md 2>/dev/null`

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

See `$bd-cli` → `reference/workflow-schema.md` for the `metric_chart_rule` action JSON shape.

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

## Wiring into the workflow

Attach a `metric_chart_rule` action to the IssueMatch step. The `add_field` names become available as `group_by` dimensions:

```json
{
  "rule_id": "crash-by-category",
  "metric_chart_rule": {
    "time_series": [{
      "count": { "value": { "match_id": "issue-step" } }
    }],
    "group_by": { "values": [{ "field_key": "error_category" }] }
  }
}
```

See `$bd-cli` → `reference/workflow-schema.md` for full action shapes.

---

## Pitfalls

| Mistake | Fix |
|---|---|
| `add_field` value is a raw error message or user ID | Bucket into a small set of enum strings first |
| Emitting all feature flags as separate field names | Unknown flag count → cardinality explosion; iterate and emit only known flags |
| No `Plot Chart` action attached | `add_field` emissions are invisible without a downstream chart action |
| Using `abort` then `add_field` later | `abort` discards all modifications including prior `add_field` calls |
