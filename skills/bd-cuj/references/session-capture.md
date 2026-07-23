# Session Capture Reference

> In the CUJ skill, session capture is integrated into the funnel workflow via a `flush_rule` + `slow_key_step` measure_time rule (see [funnel.md](funnel.md)) rather than deployed as a separate workflow. This reference describes the configuration for standalone use or when extending existing workflows.

Captures sessions when a measured duration exceeds a threshold. Requires a `measure_time_rule` with `measure_time_condition` to feed the `flush_rule`.

---

## P95 threshold

Use the threshold confirmed in Phase 4 (Alerts). If it was deferred (insufficient data), ask the user to provide an estimate in seconds now, or defer this phase until data is available.

---

## Template

A separate workflow with the same key step matchers as Phase 3, but with a `measure_time_condition` that triggers session capture only when duration exceeds the threshold.

```json
{
  "name": "{{JOURNEY_NAME}} — {{KEY_STEP_START}} to {{KEY_STEP_END}} Slow Session Capture",
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
      "rule_id": "slow_key_step",
      "measure_time_rule": {
        "name": "Slow: {{KEY_STEP_START}} → {{KEY_STEP_END}}",
        "start_match_id": "key_step_start",
        "end_match_id": "key_step_end",
        "measure_time_condition": {
          "duration_threshold": "{{P95_THRESHOLD_S}}s",
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

`duration_threshold` is in seconds. Convert the p95 threshold from milliseconds: e.g. 3000ms → `"3s"`. Add the CUJ scope field to both step matchers if defined in discovery.

Adjust `applied_daily_limit` based on journey volume — 100 is appropriate for most journeys; lower for very high-traffic flows to manage data volume.

---

## Deploy

```bash
bd workflow create session-capture.json
bd workflow deploy {{SESSION_CAPTURE_WORKFLOW_ID}}
```

---

## Investigating captured sessions

Once sessions are captured:

```bash
bd workflow captured-sessions {{SESSION_CAPTURE_WORKFLOW_ID}} -o jsonl --last 7d --limit 10 \
  --jq '{session_id, captured_at}'

bd timeline hydrate {{SESSION_ID}} --poll-interval-seconds 2
bd timeline logs {{SESSION_ID}} -o json --max-logs 500 2>/dev/null
```

The `measure_time_rule` name set above appears as a labelled event in the session timeline, making the slow span easy to locate.

---

## Gate

Report: workflow ID and link.

Then ask: "Ready to move on to the dashboard build?"
