# Phase 2: Funnel

> For workflow creation syntax, match type reference, and `--chart-metadata-file` usage, see the workflows recipe in `$bd-cli`.

This phase deploys two workflows:

1. **Funnel workflow** — conversion funnel + key step duration timing + slow session capture (all in one workflow)
2. **Completion rate workflow** — an ungrouped success rate chart (end count ÷ start count) kept separate for SLO alerting

---

## Workflow 1: Funnel

Before deploying, present the step order from Phase 0 and ask:

> "Here are the funnel steps in order — does this sequence look right, or would you like to reorder or remove any steps?"

Wait for confirmation, then build the workflow.

### Match type

Use `ootb_match: SCREEN_VIEW` for steps identified by screen name. Replace with `generic_match` on the appropriate field if using analytics events or log messages.

### Template

```json
{
  "name": "{{JOURNEY_NAME}} — Funnel",
  "flows": [
    {
      "steps": [
        {
          "match_rule": {
            "match_id": "step_1",
            "ootb_match": {
              "generic_condition": "SCREEN_VIEW",
              "generic_match": {
                "and_matcher": {
                  "matchers": [
                    {
                      "base_matcher": {
                        "log_field": "_screen_name",
                        "operator": "EQUAL",
                        "string_value": "{{STEP_1_VALUE}}"
                      }
                    }
                  ]
                }
              }
            }
          }
        },
        {
          "match_rule": {
            "match_id": "step_2",
            "ootb_match": {
              "generic_condition": "SCREEN_VIEW",
              "generic_match": {
                "and_matcher": {
                  "matchers": [
                    {
                      "base_matcher": {
                        "log_field": "_screen_name",
                        "operator": "EQUAL",
                        "string_value": "{{STEP_2_VALUE}}"
                      }
                    }
                  ]
                }
              }
            }
          }
        }
      ]
    }
  ],
  "actions": [
    {
      "rule_id": "funnel",
      "funnel_rule": {
        "match_ids": ["step_1", "step_2"]
      }
    },
    {
      "rule_id": "timing_key_step",
      "measure_time_rule": {
        "name": "{{KEY_STEP_START}} → {{KEY_STEP_END}}",
        "start_match_id": "{{KEY_STEP_START_MATCH_ID}}",
        "end_match_id": "{{KEY_STEP_END_MATCH_ID}}",
        "additional_extracted_fields": []
      }
    },
    {
      "rule_id": "histogram_key_step",
      "metric_chart_rule": {
        "time_series": [
          {
            "histogram": {
              "value": {
                "match_id": "timing_key_step",
                "name": "_duration_ms"
              }
            }
          }
        ]
      }
    },
    {
      "rule_id": "slow_key_step",
      "measure_time_rule": {
        "name": "Slow: {{KEY_STEP_START}} → {{KEY_STEP_END}}",
        "start_match_id": "{{KEY_STEP_START_MATCH_ID}}",
        "end_match_id": "{{KEY_STEP_END_MATCH_ID}}",
        "measure_time_condition": {
          "duration_threshold": "5s",
          "operator": "GREATER_THAN"
        },
        "additional_extracted_fields": []
      }
    },
    {
      "rule_id": "capture_slow_key_step",
      "flush_rule": {
        "applied_daily_limit": 100,
        "match_id": "slow_key_step"
      }
    }
  ],
  "platform_targets": [
    { "apple":   { "apps": [{ "app_id": "{{IOS_BUNDLE_ID}}" }] } },
    { "android": { "apps": [{ "app_id": "{{ANDROID_PACKAGE}}" }] } }
  ]
}
```

**Notes:**
- Add a step block and a `match_ids` entry for each additional funnel step.
- Add the CUJ scope field to every step's `and_matcher` if defined in discovery.
- `{{KEY_STEP_START_MATCH_ID}}` and `{{KEY_STEP_END_MATCH_ID}}` are the `match_id` values of the key step's start and end steps (e.g. `step_3` and `step_4`).
- `slow_key_step` uses a placeholder threshold of `"5s"`. This will be updated to the confirmed p95 in Phase 4 once baseline data is available.
- `timing_key_step` has no condition — it records duration for all completions and powers the histogram. `slow_key_step` has the condition and triggers the session capture `flush_rule`.
- `applied_daily_limit: 100` is appropriate for most journeys; lower for very high-traffic flows.
- See [measure-time.md](measure-time.md) for `measure_time_rule` configuration details.
- See [session-capture.md](session-capture.md) for `flush_rule` and session investigation details.

> **Future segmentation:** Adding separate flows per payment method, or for guest vs. signed-in users, would give per-segment drop-off visibility. This can be done by updating this workflow to add additional flows later.

---

## Workflow 2: Completion Rate

This workflow counts journey starts and completions independently, then computes the ratio. It must have **no `group_by`** — the SLO alert in Phase 4 requires an ungrouped rate chart. Kept as a separate workflow for this reason.

### Template

```json
{
  "name": "{{JOURNEY_NAME}} — Completion Rate",
  "flows": [
    {
      "steps": [
        {
          "match_rule": {
            "match_id": "journey_started",
            "ootb_match": {
              "generic_condition": "SCREEN_VIEW",
              "generic_match": {
                "and_matcher": {
                  "matchers": [
                    {
                      "base_matcher": {
                        "log_field": "_screen_name",
                        "operator": "EQUAL",
                        "string_value": "{{STEP_1_VALUE}}"
                      }
                    }
                  ]
                }
              }
            }
          }
        }
      ]
    },
    {
      "steps": [
        {
          "match_rule": {
            "match_id": "journey_completed",
            "ootb_match": {
              "generic_condition": "SCREEN_VIEW",
              "generic_match": {
                "and_matcher": {
                  "matchers": [
                    {
                      "base_matcher": {
                        "log_field": "_screen_name",
                        "operator": "EQUAL",
                        "string_value": "{{LAST_STEP_VALUE}}"
                      }
                    }
                  ]
                }
              }
            }
          }
        }
      ]
    }
  ],
  "actions": [
    {
      "rule_id": "completion_rate",
      "metric_chart_rule": {
        "time_series": [
          {
            "rate": {
              "numerator": { "match_id": "journey_completed" },
              "denominator": { "match_id": "journey_started" }
            }
          }
        ]
      }
    }
  ],
  "platform_targets": [
    { "apple":   { "apps": [{ "app_id": "{{IOS_BUNDLE_ID}}" }] } },
    { "android": { "apps": [{ "app_id": "{{ANDROID_PACKAGE}}" }] } }
  ]
}
```

The two flows are independent — each counts its own event separately. The `rate` action divides completions by starts across the same time window.

---

## Chart metadata

Set readable series labels by passing `--chart-metadata-file` alongside workflow creation. Create `funnel-chart-metadata.json`:

```json
[
  {
    "rule_id": "histogram_key_step",
    "metadata": {
      "title": "{{KEY_STEP_START}} → {{KEY_STEP_END}} Duration",
      "metric_chart_metadata": {
        "time_series_display_mode": {},
        "metadata": [{ "title": "{{KEY_STEP_START}} → {{KEY_STEP_END}} Duration", "y_axis": { "description": "Duration", "unit": "MILLISECONDS" }, "sort_order": "MAX", "connector_export_config": [] }]
      }
    }
  }
]
```

And `completion-rate-chart-metadata.json`:

```json
[
  {
    "rule_id": "completion_rate",
    "metadata": {
      "title": "Completion Rate",
      "metric_chart_metadata": {
        "time_series_display_mode": {},
        "metadata": [{ "title": "Completion Rate", "y_axis": { "description": "Completion Rate", "unit": "PERCENTAGE" }, "sort_order": "MAX", "connector_export_config": [] }]
      }
    }
  }
]
```

---

## Workflow metadata

Create `funnel-metadata.json`:

```json
{
  "description": "{{JOURNEY_NAME}} CUJ funnel — step-by-step conversion, key step duration histogram ({{KEY_STEP_START}} → {{KEY_STEP_END}}), and slow session capture. Deployed as part of CUJ monitoring.",
  "per_rule_metadata": [
    { "rule_id": "funnel",               "title": "{{JOURNEY_NAME}} — Conversion Funnel" },
    { "rule_id": "timing_key_step",      "title": "{{KEY_STEP_START}} → {{KEY_STEP_END}} Timing" },
    { "rule_id": "histogram_key_step",   "title": "{{KEY_STEP_START}} → {{KEY_STEP_END}} Duration" },
    { "rule_id": "slow_key_step",        "title": "Slow: {{KEY_STEP_START}} → {{KEY_STEP_END}}" },
    { "rule_id": "capture_slow_key_step","title": "Slow Session Capture" }
  ]
}
```

Create `completion-rate-metadata.json`:

```json
{
  "description": "{{JOURNEY_NAME}} CUJ completion rate — ungrouped start-to-completion ratio for SLO alerting. Kept separate from the funnel workflow because SLO alerts require an ungrouped rate chart.",
  "per_rule_metadata": [
    { "rule_id": "completion_rate", "title": "{{JOURNEY_NAME}} — Completion Rate" }
  ]
}
```

---

## Deploy

```bash
bd workflow create funnel.json \
  --metadata-file funnel-metadata.json \
  --chart-metadata-file funnel-chart-metadata.json
bd workflow deploy {{FUNNEL_WORKFLOW_ID}}

bd workflow create completion-rate.json \
  --metadata-file completion-rate-metadata.json \
  --chart-metadata-file completion-rate-chart-metadata.json
bd workflow deploy {{COMPLETION_RATE_WORKFLOW_ID}}
```

Note both workflow IDs — they are referenced in Phase 4 (alerts) and Phase 5 (dashboard).

> **Completion rate caveat:** The completion rate workflow counts journey start events and completion events independently across all traffic. If the completion event (e.g. a home screen) is also reached by users who never went through this journey, the rate can exceed 100%. This is expected behaviour — the metric is most meaningful for journeys where the start event is a reliable proxy for journey entry. Review the chart after a few days and adjust the target accordingly.

---

## Gate

Report: both workflow IDs and their links (`bd workflow open ... -o json --jq .url -r`).

Then ask: "Ready to continue to Phase 3 — Network?"
