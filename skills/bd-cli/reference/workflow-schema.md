# Workflow Schema

A **workflow** is the core building block for monitoring mobile app behavior. It defines rules for matching event sequences and what to do when they fire. Workflows compile to finite state machines pushed to every SDK instance — evaluation is on-device; no raw logs leave unless a `flush_rule` is present.

**Two use cases:**
- **Charts & Metrics** — on-device aggregation surfaced as dashboard panels
- **Session Capture** — flush full buffered logs to backend for timeline inspection

Model a workflow around **one coherent on-device detection or measurement problem**. If multiple
entry points represent different questions, journeys, or operational surfaces, prefer multiple
workflows and compose their chart outputs in a dashboard instead of forcing them into one workflow.

> **Structural reference:** Use `bd schema workflow.create Workflow --depth 2` for the live proto
> schema. This document focuses on patterns, pitfalls, and domain knowledge that the schema alone
> doesn't convey.

---

## Core Structure

For the top-level shape: `bd schema workflow.create Workflow --depth 0`

`platform_targets` — omit to match all. Options: `{"android": {}}`, `{"apple": {}}`, `{"electron": {}}`. Scope to a specific app: `{"android": {"apps": [{"app_id": "com.example"}]}}`.

---

## Flows and Steps

A flow is an ordered list of steps matched sequentially. When all steps match, the flow resets and counts again. A step matches independently on-device; no cross-device aggregation occurs until the metric is flushed.

**Execution type (top-level field on each flow — pick one):**
- `exclusive` (default) — re-match from step 0 on overlap
- `parallel` with `max_active_runs` — multiple in-flight runs; use for NETWORK_REQUEST/RESPONSE correlation

### Match types

`match_rule` has `match_id` and exactly one match type. Use `bd schema workflow.create MatchRule
--depth 2` for the full shape.

| Key | Use |
|---|---|
| `ootb_match` | Built-in SDK event (`NETWORK_RESPONSE`, `APP_OPEN`, `RESOURCE`, etc.). Use `bd schema workflow.create OotbMatch --docs` for the live condition list and enum docs. Drill into a specific event with `bd schema workflow.create GenericOotbConditionType.<VALUE>` for field keys, types, and platform tags |
| `generic_match` | Custom log field / compound condition tree |
| `state_change_match` | Feature flag or state transition |
| `known_entity_match` | Matches any event from a bookmarked (known) entity. Empty message — no fields. Use for VIP session capture |

Use `generic_condition` for cross-platform workflows. `android_condition` / `apple_condition` are accepted by the API but show a violation in the UI when the workflow targets both platforms.

`sample_rate` — numerator out of 1,000,000. `1000000` = 100%, `10000` = 1%. Omit for 100%.

### Key patterns

**Known entity (VIP) capture** — fires on any event from a bookmarked entity. Requires the app to call `setEntityID`/`setEntityId` and the entity to be bookmarked in the UI or via `bd entity known upsert`:
```json
{
  "match_id": "vip-session",
  "known_entity_match": {}
}
```
Pair with a `flush_rule` referencing `"vip-session"` to guarantee full session capture for all bookmarked entities.

**OOTB + field filter** (AND an ootb event with a field condition):
```json
{
  "match_id": "checkout-response",
  "ootb_match": {
    "generic_condition": "NETWORK_RESPONSE",
    "generic_match": { "base_matcher": { "log_field": "_path_template", "operator": "EQUAL", "string_value": "/api/checkout" } }
  }
}
```

**Custom log match:**
```json
{ "match_id": "payment-failed", "generic_match": { "base_matcher": { "log_field": "action", "operator": "EQUAL", "string_value": "payment_error" } } }
```

Common built-in log fields for `generic_match`:

- `log` — log body text; use `REGEX .*` to match any log
- `log_level` — integer severity: `0=Trace`, `1=Debug`, `2=Info`, `3=Warning`, `4=Error`

**Compound (AND/OR):** wrap in `and_matcher` or `or_matcher` with a `matchers[]` array of `generic_match` objects. `not_matcher` takes a single `generic_match_condition`.

**Feature flag match:**
```json
{ "match_id": "flag-on", "state_change_match": { "scope": "FEATURE_FLAG_EXPOSURE", "key": "cart_v2", "to": { "value": "true" } } }
```

### Operators

Use `bd schema workflow.create MatchRule --depth 2` for the live operator enum and LHS/RHS options.

Gotchas: `IN` / `NOT_IN` values are separated by `~~` in `string_value`. `SET` / `NOT_SET` still requires a dummy RHS: `"string_value": ""`.

---

## Exit Conditions

Attach to any step except step 0 (exit conditions on step 0 are not allowed). Fire when the next step doesn't complete as expected, resetting the flow. Exit `id` / `match_id` values can be referenced in actions just like step `match_id`s.

```json
{
  "match_rule": { "match_id": "s2", "ootb_match": { "generic_condition": "APP_OPEN" } },
  "exit_conditions": [
    { "timeout": { "id": "s2-timeout", "timeout_rule": { "duration": 10, "duration_unit": "SECONDS" } } },
    { "match_rule": { "match_id": "user-left", "ootb_match": { "generic_condition": "APP_BACKGROUND" } } }
  ]
}
```

**Pattern:** deploy with `measure_time_rule` histogram first → observe p50/p95 → add timeout at ~2× p95 → reference timeout ID in `flush_rule` to capture only outlier sessions.

---

## Actions

Every action has a `rule_id` and exactly one action type. Use `bd schema workflow.create ActionRule
--depth 2` for the full action shape.

### Session Capture (`flush_rule`)
```json
{ "rule_id": "capture", "flush_rule": { "match_id": "step-or-timeout-id" } }
```
Omit `applied_daily_limit` — server-managed.

### Measure Time (`measure_time_rule`)
```json
{ "rule_id": "dur", "measure_time_rule": { "name": "checkout-duration", "start_match_id": "s1", "end_match_id": "s3" } }
```

### Metric Chart (`metric_chart_rule`)

**Count:**
```json
{ "rule_id": "opens", "metric_chart_rule": { "time_series": [{ "count": { "value": { "match_id": "s1" } } }] } }
```

**Rate** (requires two separate flows — one for all, one for success):
```json
{ "rule_id": "rate", "metric_chart_rule": { "time_series": [{ "rate": { "numerator": { "match_id": "success-step" }, "denominator": { "match_id": "all-step" } } }] } }
```

**Histogram of measure_time_rule duration:**
```json
{ "histogram": { "value": { "match_id": "dur-rule-id", "measured_time": true } } }
```

**Histogram of a numeric field (e.g. memory, request size):**
```json
{ "histogram": { "value": { "match_id": "s1", "name": "_jvm_used_kb" } } }
```

**Average (numeric field average per aggregation window):**
```json
{ "average_count": { "numerator": { "match_id": "s1", "name": "_duration_ms" } } }
```
Like `rate` but the denominator is implicit (auto-incremented on each match). Display is not percentage-based — shows the raw average value.

Multiple `time_series` entries referencing different `name` fields from the same step are valid (one flow, multiple chart series) — not possible in the UI.

**`group_by` (split by dimension):**
```json
"group_by": { "values": [{ "field_key": "_app_version" }] }
"group_by": { "values": [{ "state_value": { "scope": "FEATURE_FLAG_EXPOSURE", "key": "flag_name" } }] }
```

### Funnel (`funnel_rule`)

Shows what percentage of users reach each step. Useful for any multi-step flow.

```json
{ "rule_id": "funnel", "funnel_rule": { "match_ids": ["s1", "s2", "s3"] } }
```

Omit `ids` — server auto-generates from `match_ids`.

#### Action patterns for funnels

- **`funnel_rule`** — understand where users drop off. Shows step-by-step completion rates.
- **Timeout exit condition + `flush_rule`** — debug why users don't complete a step. Captures full session logs when the next event doesn't arrive within the expected window.
- **`measure_time_rule` + histogram** — baseline and monitor step latency. Deploy first, observe p50/p95, then set timeout at ~2× p95.
- **`group_by state_value` with `FEATURE_FLAG_EXPOSURE`** — compare behavior across flag variants.

### Sankey Diagram (`sankey_diagram_rule`)
```json
{
  "rule_id": "sankey",
  "sankey_diagram_rule": {
    "nodes": [
      { "id": "s1", "fixed": "App Open" },
      { "id": "s2", "extract_field": "_screen_name" },
      { "id": "s3", "fixed": "ANR" }
    ]
  }
}
```

**Loop pattern** (collect every screen view between two events): set `loop_match_id` on the middle step pointing to itself — requires a `sankey_diagram_rule` that references it. Sankey terminal step must be a **regular step**, not an exit condition.

---

## OOTB Match Gotchas

### Network and GraphQL
- Use `_result == "success"` rather than `_status_code < 400`.
- Use `_path_template`, not `_path`, for `group_by` or durable alert-style workflows. `_path` is
  usually too high-cardinality (`/users/123`, `/users/456`, ...).

### Deprecated / conditional events
- **`APP_EXIT`** — Android-only deprecated alias. Do not use for new workflows; prefer
  `APP_TERMINATION`.
- **`SESSION_REPLAY`** — present in all three condition enums, but only relevant when Session
  Replay is enabled for the app.
