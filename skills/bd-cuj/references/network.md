# Phase 3: Network

> For workflow creation syntax and `--chart-metadata-file` usage, see the workflows recipe in `$bd-cli`.

If the user skipped network scope in Phase 0, skip this phase entirely and proceed to Phase 4.

Monitors the API calls behind the journey: request volume, success rate, and latency.

---

## `_path` vs `_path_template`

**Always use `_path` in matcher conditions. Use `_path_template` only in `group_by_fields`.**

- `_path` — the actual request path as received (e.g. `/api/v1/user/12345`). Use this in matchers.
- `_path_template` — a normalized form with variable segments collapsed (e.g. `/api/v1/user/<id>`). Use this in `group_by_fields` so charts show one series per endpoint pattern rather than one per unique ID.

For matching:
- **Static path** (no variable segments): `"log_field": "_path", "operator": "EQUAL", "string_value": "/api/v1/graphql"`
- **Dynamic path** (contains IDs or other variable segments): `"log_field": "_path", "operator": "REGEX", "string_value": "/api/v1/user/.*"`

---

## Multi-path and multi-host

If the journey touches multiple paths on the same host, you have two options:

1. **One workflow per path** — simplest; each workflow scopes to one host + one path. Scale this across paths.
2. **One workflow, host-only match** — omit the path condition and add `"group_by_fields": ["_path_template"]` at the top level of the workflow JSON. The chart will show one series per path template automatically.

> **Warning:** Do not use `or_matcher` as the root of `generic_match`. The API accepts it but the workflow page fails to render in the UI. Always use `and_matcher` at the root, with `or_matcher` nested inside for multi-value conditions on a single field.

If the journey touches multiple API hosts, create one workflow per host.

---

## Template

Two flows are sufficient: `all_responses` (for request count and latency) and `success_responses` (for success rate).

```json
{
  "name": "{{JOURNEY_NAME}} — {{HOST}} Network",
  "flows": [
    {
      "steps": [{
        "match_rule": {
          "match_id": "all_responses",
          "ootb_match": {
            "generic_condition": "NETWORK_RESPONSE",
            "generic_match": {
              "and_matcher": {
                "matchers": [
                  { "base_matcher": { "log_field": "_host", "operator": "EQUAL", "string_value": "{{HOST}}" } },
                  { "base_matcher": { "log_field": "_path", "operator": "EQUAL", "string_value": "{{PATH}}" } }
                ]
              }
            }
          }
        }
      }]
    },
    {
      "steps": [{
        "match_rule": {
          "match_id": "success_responses",
          "ootb_match": {
            "generic_condition": "NETWORK_RESPONSE",
            "generic_match": {
              "and_matcher": {
                "matchers": [
                  { "base_matcher": { "log_field": "_host",   "operator": "EQUAL", "string_value": "{{HOST}}" } },
                  { "base_matcher": { "log_field": "_path",   "operator": "EQUAL", "string_value": "{{PATH}}" } },
                  { "base_matcher": { "log_field": "_result", "operator": "EQUAL", "string_value": "success" } }
                ]
              }
            }
          }
        }
      }]
    }
  ],
  "actions": [
    {
      "rule_id": "request_count",
      "metric_chart_rule": {
        "time_series": [{ "count": { "value": { "match_id": "all_responses" } } }]
      }
    },
    {
      "rule_id": "success_rate",
      "metric_chart_rule": {
        "time_series": [{
          "rate": {
            "numerator": { "match_id": "success_responses" },
            "denominator": { "match_id": "all_responses" }
          }
        }]
      }
    },
    {
      "rule_id": "latency",
      "metric_chart_rule": {
        "time_series": [{
          "histogram": {
            "value": { "match_id": "all_responses", "name": "_duration_ms" }
          }
        }]
      }
    }
  ],
  "platform_targets": [
    { "apple":   { "apps": [{ "app_id": "{{IOS_BUNDLE_ID}}" }] } },
    { "android": { "apps": [{ "app_id": "{{ANDROID_PACKAGE}}" }] } }
  ]
}
```

Use `_result == "success"` for the success numerator — do not filter by status code.

> **Note:** This workflow's success rate chart cannot be used for SLO alerting (SLOs require an ungrouped rate). If per-endpoint SLOs are needed, create a separate completion-rate-style workflow per path (one `all_responses` flow + one `success_responses` flow, no `group_by_fields`).

---

## Chart metadata

Set readable series labels by passing `--chart-metadata-file` alongside workflow creation. Create a file with one entry per chart rule:

```json
[
  {
    "rule_id": "request_count",
    "metadata": {
      "title": "Request Count",
      "metric_chart_metadata": {
        "time_series_display_mode": {},
        "metadata": [{ "title": "Request Count", "y_axis": { "description": "Requests", "unit": "COUNT" }, "sort_order": "MAX", "connector_export_config": [] }]
      }
    }
  },
  {
    "rule_id": "success_rate",
    "metadata": {
      "title": "Success Rate",
      "metric_chart_metadata": {
        "time_series_display_mode": {},
        "metadata": [{ "title": "Success Rate", "y_axis": { "description": "Success Rate", "unit": "PERCENTAGE" }, "sort_order": "MAX", "connector_export_config": [] }]
      }
    }
  },
  {
    "rule_id": "latency",
    "metadata": {
      "title": "Latency",
      "metric_chart_metadata": {
        "time_series_display_mode": {},
        "metadata": [{ "title": "Latency", "y_axis": { "description": "Duration", "unit": "MILLISECONDS" }, "sort_order": "MAX", "connector_export_config": [] }]
      }
    }
  }
]
```

Note: `--chart-metadata-file` only accepts one item per call when `--workflow-file` is omitted. Pass all entries in a single file alongside `bd workflow create`.

---

## Workflow metadata

Create `network-metadata.json`:

```json
{
  "description": "{{JOURNEY_NAME}} CUJ network — RED metrics (request count, success rate, latency) for {{HOST}} API calls during the journey. Deployed as part of CUJ monitoring.",
  "per_rule_metadata": [
    { "rule_id": "request_count", "title": "Request Count" },
    { "rule_id": "success_rate",  "title": "Success Rate" },
    { "rule_id": "latency",       "title": "Latency" }
  ]
}
```

---

## Deploy

```bash
bd workflow create network.json \
  --metadata-file network-metadata.json \
  --chart-metadata-file network-chart-metadata.json
bd workflow deploy {{NETWORK_WORKFLOW_ID}}
```

Note this workflow ID — it is referenced in Phase 4 (dashboard). The rule IDs `request_count`, `success_rate`, and `latency` are stable and used directly in the dashboard payload.

---

## Gate

Report: workflow ID(s) and link(s).

Then ask: "Ready to continue to Phase 4 — Alerts?"
