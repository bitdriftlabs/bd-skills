# Authoring Chart Rules

This recipe covers the decisions behind writing chart actions in a workflow — which type to use,
how they wire to flows, and common patterns. For the raw field shapes, use `bd schema workflow.create
ActionRule --depth 2`. For display configuration (titles, units, series labels), see
[chart-metadata.md](./chart-metadata.md).

---

## Which chart type to use

| Question | Chart type |
|---|---|
| How many times did X happen? | `metric_chart_rule` — count |
| What fraction of X events were successful? | `metric_chart_rule` — rate |
| How long does the journey from A to B take? | `measure_time_rule` + `metric_chart_rule` — histogram |
| What is the average value of a numeric field? | `metric_chart_rule` — average_count |
| What fraction of users complete a multi-step flow? | `funnel_rule` |
| What paths do users take between two events? | `sankey_diagram_rule` |

---

## Count

One flow, one action. Use for raw event volume: sessions, API calls, screen views, errors.

```json
{
  "flows": [
    { "exclusive": {}, "steps": [{ "match_rule": { "match_id": "event", "ootb_match": { "generic_condition": "APP_OPEN" } } }] }
  ],
  "actions": [
    { "rule_id": "open_count", "metric_chart_rule": { "time_series": [{ "count": { "value": { "match_id": "event" } } }] } }
  ]
}
```

---

## Rate (success rate, error rate)

Rate charts need **two separate flows** — one for all events, one for the qualifying subset. A single
flow cannot express "count of N that satisfy condition / count of all N." The two flows are
independent; the rate action references both as numerator and denominator.

```json
{
  "flows": [
    {
      "exclusive": {},
      "steps": [{ "match_rule": { "match_id": "all_responses", "ootb_match": { "generic_condition": "NETWORK_RESPONSE",
        "generic_match": { "base_matcher": { "log_field": "_host", "operator": "EQUAL", "string_value": "api.example.com" } } } } }]
    },
    {
      "exclusive": {},
      "steps": [{ "match_rule": { "match_id": "success_responses", "ootb_match": { "generic_condition": "NETWORK_RESPONSE",
        "generic_match": { "and_matcher": { "matchers": [
          { "base_matcher": { "log_field": "_host", "operator": "EQUAL", "string_value": "api.example.com" } },
          { "base_matcher": { "log_field": "_result", "operator": "EQUAL", "string_value": "success" } }
        ]}}}}]
    }
  ],
  "actions": [
    { "rule_id": "success_rate", "metric_chart_rule": { "time_series": [{
      "rate": { "numerator": { "match_id": "success_responses" }, "denominator": { "match_id": "all_responses" } }
    }]}}
  ]
}
```

**Network success rate:** always use `_result == "success"` as the numerator condition, not
`_status_code < 400`. `_result` is normalized and handles edge cases that raw status codes miss.

---

## Histogram (latency / duration)

Histograms require a `measure_time_rule` to define the measurement, then a `metric_chart_rule`
that references it by `rule_id` via `measured_time: true`.

```json
{
  "flows": [
    { "exclusive": {}, "steps": [
      { "match_rule": { "match_id": "start", "ootb_match": { "generic_condition": "SCREEN_VIEW",
        "generic_match": { "base_matcher": { "log_field": "_screen_name", "operator": "EQUAL", "string_value": "Checkout" } } } } },
      { "match_rule": { "match_id": "end", "ootb_match": { "generic_condition": "SCREEN_VIEW",
        "generic_match": { "base_matcher": { "log_field": "_screen_name", "operator": "EQUAL", "string_value": "Confirmation" } } } } }
    ]}
  ],
  "actions": [
    { "rule_id": "timing", "measure_time_rule": { "name": "checkout-duration", "start_match_id": "start", "end_match_id": "end" } },
    { "rule_id": "duration_histogram", "metric_chart_rule": { "time_series": [{
      "histogram": { "value": { "match_id": "timing", "measured_time": true } }
    }]}}
  ]
}
```

You can also histogram a **numeric field** (e.g. response size, memory):

```json
{ "histogram": { "value": { "match_id": "network_event", "name": "_response_body_size" } } }
```

---

## Average

Use when you want the mean of a numeric field per aggregation window, not a distribution. Syntax
is similar to rate but the denominator is implicit (auto-incremented on every match):

```json
{ "average_count": { "numerator": { "match_id": "event", "name": "_duration_ms" } } }
```

Prefer **histogram** over average for latency — histograms show P50/P95/P99 and reveal tail behavior
that averages hide. Use average for values where distribution shape isn't the question (e.g. mean
active session count, mean payload size as a throughput proxy).

---

## Funnel

Use for multi-step flows where the question is **where do users drop off**. `match_ids` defines
the ordered steps; the funnel chart shows completion percentage at each step.

```json
{ "rule_id": "funnel", "funnel_rule": { "match_ids": ["step1", "step2", "step3"] } }
```

**Funnel vs completion rate workflow:**
- `funnel_rule` in the same workflow shows the per-step drop-off chart.
- A separate workflow with a rate action (numerator = final step, denominator = first step) gives a
  single time-series completion rate you can alert on. Use both: funnel for diagnosis, rate for
  alerting.

---

## Sankey

Use for path discovery — what paths do users take between two anchor events?

```json
{ "rule_id": "paths", "sankey_diagram_rule": { "nodes": [
  { "id": "start", "fixed": "App Open" },
  { "id": "middle", "extract_field": "_screen_name" },
  { "id": "end", "fixed": "Purchase" }
]}}
```

The middle node with `extract_field` captures the actual field value from each event. Use the
**loop pattern** to collect every screen view between the anchors by setting `loop_match_id` on the
middle step.

Sankey has no chart metadata — `--chart-metadata-file` is not needed for sankey rules.

---

## group_by: splitting a chart by dimension

Add `group_by` inside a `time_series` entry to break a metric out by a field value (e.g. app
version, platform, endpoint). Each distinct value becomes a separate series.

```json
{ "count": { "value": { "match_id": "crash" } }, "group_by": { "values": [{ "field_key": "_app_version" }] } }
```

**When to use group_by vs separate workflows:**
- **group_by** — the dimension is dynamic and you want all values in one chart (versions, paths,
  platforms). Use `_path_template` not `_path` for network endpoints to avoid cardinality explosion.
- **Separate workflows** — each entry point represents a distinct operational question, or you need
  to alert per-endpoint (SLO alerts cannot be attached to grouped charts).

**Feature flag segmentation:**

```json
"group_by": { "values": [{ "state_value": { "scope": "FEATURE_FLAG_EXPOSURE", "key": "flag_name" } }] }
```

---

## Wiring chart metadata

`--chart-metadata-file` requires knowing each `rule_id` and the number of `time_series` entries
per rule. Without it, the UI shows raw aggregated action IDs as series labels. See
[chart-metadata.md](./chart-metadata.md) for format and update patterns.
