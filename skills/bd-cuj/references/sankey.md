# Phase 1: Sankey

> For workflow creation syntax and `--chart-metadata-file` usage, see the workflows recipe in `$bd-cli`.

A sankey shows all paths users take between the journey's start and end. Deploy it first — it reveals whether the expected golden path matches actual user behaviour before you commit to a funnel.

---

## Middle step

The sankey middle step loops between start and end, extracting the field that identifies each screen or event. Ask the user:

> "For the sankey middle step, should I use screen names (bitdrift screen view API) or the same event field as your steps? Screen names give the richest path breakdown if screen tracking is enabled."

- **Screen names** → use `SCREEN_VIEW` OOTB with `extract_field: "_screen_name"`
- **Analytics events / logs** → use a `generic_match` loop on the event field, extracting its value

---

## Template

Use `ootb_match: SCREEN_VIEW` for all three steps when using screen names. Replace with `generic_match` on the appropriate field if using analytics events or log messages.

```json
{
  "name": "{{JOURNEY_NAME}} — Path Discovery",
  "flows": [
    {
      "steps": [
        {
          "match_rule": {
            "match_id": "start",
            "ootb_match": {
              "generic_condition": "SCREEN_VIEW",
              "generic_match": {
                "and_matcher": {
                  "matchers": [
                    {
                      "base_matcher": {
                        "log_field": "_screen_name",
                        "operator": "EQUAL",
                        "string_value": "{{START_VALUE}}"
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
            "match_id": "middle",
            "ootb_match": {
              "generic_condition": "SCREEN_VIEW"
            }
          },
          "loop_match_id": "middle"
        },
        {
          "match_rule": {
            "match_id": "end",
            "ootb_match": {
              "generic_condition": "SCREEN_VIEW",
              "generic_match": {
                "and_matcher": {
                  "matchers": [
                    {
                      "base_matcher": {
                        "log_field": "_screen_name",
                        "operator": "EQUAL",
                        "string_value": "{{END_VALUE}}"
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
      "rule_id": "sankey",
      "sankey_diagram_rule": {
        "nodes": [
          { "id": "start",  "fixed": "{{START_LABEL}}" },
          { "id": "middle", "extract_field": "_screen_name" },
          { "id": "end",    "fixed": "{{END_LABEL}}" }
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

**Notes:**
- If a CUJ scope field was defined in discovery, add it as an additional matcher to every step's `and_matcher`.
- Omit `platform_targets` entries for platforms not in scope.
- Run `bd schema workflow.create` to verify the current payload shape before deploying.

---

## Workflow metadata

Create `sankey-metadata.json`:

```json
{
  "description": "{{JOURNEY_NAME}} path discovery — surfaces all routes users take between journey start and end. Deployed as part of CUJ monitoring.",
  "per_rule_metadata": [
    { "rule_id": "sankey", "title": "{{JOURNEY_NAME}} — User Paths" }
  ]
}
```

---

## Deploy

The sankey chart has no metric series, so `--chart-metadata-file` is not required.

```bash
bd workflow create sankey.json --metadata-file sankey-metadata.json
bd workflow deploy {{WORKFLOW_ID}}
```

Wait at least 24 hours for meaningful traffic before reading the chart.

---

## Gate

Report: workflow ID and `bd workflow open {{WORKFLOW_ID}} -o json --jq .url -r`.

Then ask: "Ready to continue to Phase 2 — Funnel?"
