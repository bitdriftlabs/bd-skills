# Measure Time Reference

> In the CUJ skill, `measure_time_rule` is added directly to the funnel workflow (see [funnel.md](funnel.md)) rather than deployed as a separate workflow. This reference describes the rule configuration for standalone use or when extending existing workflows.

Measures the duration between two matched steps. The rule produces a `_duration_ms` value that can be consumed by a histogram `metric_chart_rule` for charting, or by a `flush_rule` (optionally with a `measure_time_condition`) for session capture.

---

## Template

```json
{
  "name": "{{JOURNEY_NAME}} — {{KEY_STEP_START}} to {{KEY_STEP_END}} Duration",
  "flows": [
    {
      "steps": [
        {
          "match_rule": {
            "match_id": "key_step_start",
            "generic_match": {
              "and_matcher": {
                "matchers": [
                  {
                    "base_matcher": {
                      "log_field": "{{KEY_STEP_START_FIELD}}",
                      "operator": "EQUAL",
                      "string_value": "{{KEY_STEP_START_VALUE}}"
                    }
                  }
                ]
              }
            }
          }
        },
        {
          "match_rule": {
            "match_id": "key_step_end",
            "generic_match": {
              "and_matcher": {
                "matchers": [
                  {
                    "base_matcher": {
                      "log_field": "{{KEY_STEP_END_FIELD}}",
                      "operator": "EQUAL",
                      "string_value": "{{KEY_STEP_END_VALUE}}"
                    }
                  }
                ]
              }
            }
          }
        }
      ]
    }
  ],
  "actions": [
    {
      "rule_id": "timing_key_step",
      "measure_time_rule": {
        "name": "{{KEY_STEP_START}} → {{KEY_STEP_END}}",
        "start_match_id": "key_step_start",
        "end_match_id": "key_step_end",
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
    }
  ],
  "platform_targets": [
    { "apple":   { "apps": [{ "app_id": "{{IOS_BUNDLE_ID}}" }] } },
    { "android": { "apps": [{ "app_id": "{{ANDROID_PACKAGE}}" }] } }
  ]
}
```

Add the CUJ scope field to both steps' `and_matcher` if defined in discovery.

---

## Deploy

```bash
bd workflow create measure-time.json
bd workflow deploy {{MEASURE_TIME_WORKFLOW_ID}}
```

Allow at least 7 days of data to accumulate before reading p50/p95 baselines for alerting.
