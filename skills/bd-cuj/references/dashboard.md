# Phase 5: Dashboard

Creates a two-tab dashboard assembling all deployed workflows. Build this after all preceding phases are deployed and live.

---

## Completeness check

Before building the payload, list all workflow IDs created in Phases 1–3 and confirm every chart-producing rule has a corresponding panel in the layout below. Workflows without a dashboard panel are invisible to users.

| Workflow | Rules to surface |
|---|---|
| Sankey (Phase 1) | `sankey` |
| Funnel (Phase 2) | `funnel`, `histogram_key_step` |
| Completion Rate (Phase 2) | `completion_rate` |
| Network (Phase 3, if deployed) | `success_rate`, `latency`, `request_count` |

---

## Collect rule IDs

For each workflow, extract the `rule_id` values needed by the dashboard payload:

```bash
bd workflow describe {{WORKFLOW_ID}} -o json --jq '.workflow.actions[] | {rule_id}'
```

---

## Layout

The dashboard uses a 12-column grid. Every chart requires `x`, `y`, `column_span`, and `row_span` in `layout_settings` — the API rejects payloads missing any of these.

**Tab 1 — Journey**

| Chart | x | y | column_span | row_span |
|---|---|---|---|---|
| Sankey | 0 | 0 | 12 | 4 |
| Funnel | 0 | 4 | 6 | 4 |
| Completion Rate | 6 | 4 | 6 | 4 |
| Key Step Histogram | 0 | 8 | 12 | 4 |

**Tab 2 — Network** (omit if Phase 3 was skipped)

| Chart | x | y | column_span | row_span |
|---|---|---|---|---|
| Success Rate | 0 | 0 | 12 | 4 |
| Latency | 0 | 4 | 12 | 4 |
| Request Count | 0 | 8 | 12 | 4 |

---

## Series labels

Set readable series labels via `--chart-metadata-file` when creating the workflow, or update after deploy. For the CUJ dashboard the relevant rules are `completion_rate` (one rate series) and `histogram_key_step` (one histogram series — the platform appends the percentile, so title `"{{KEY_STEP_NAME}} Duration"` renders as `"{{KEY_STEP_NAME}} Duration: P50"` etc.).

See the workflows recipe in `$bd-cli` for the `--chart-metadata-file` format.

---

## Payload

```json
{
  "name": "{{JOURNEY_NAME}} CUJ",
  "tabs": [
    {
      "name": "Journey",
      "charts": [
        {
          "chart_component_layout": {
            "chart_id": { "sankey_chart": { "workflow_id": "{{SANKEY_WORKFLOW_ID}}", "rule_id": "sankey" } },
            "layout_settings": { "x": 0, "y": 0, "column_span": 12, "row_span": 4, "is_hidden": false },
            "chart_metadata": {
              "title": "{{JOURNEY_NAME}} — User Paths",
              "sankey_chart_metadata": {}
            }
          }
        },
        {
          "chart_component_layout": {
            "chart_id": { "workflow_funnel_chart": { "workflow_id": "{{FUNNEL_WORKFLOW_ID}}", "funnel_rule_id": "funnel" } },
            "layout_settings": { "x": 0, "y": 4, "column_span": 6, "row_span": 4, "is_hidden": false },
            "chart_metadata": {
              "title": "{{JOURNEY_NAME}} — Conversion",
              "funnel_chart_metadata": {
                "steps": [
                  { "name": "{{STEP_1_NAME}}" },
                  { "name": "{{STEP_2_NAME}}" }
                ]
              }
            }
          }
        },
        {
          "chart_component_layout": {
            "chart_id": { "workflow": { "workflow_id": "{{COMPLETION_RATE_WORKFLOW_ID}}", "chart_rule_id": "completion_rate" } },
            "layout_settings": { "x": 6, "y": 4, "column_span": 6, "row_span": 4, "is_hidden": false },
            "chart_metadata": {
              "title": "{{JOURNEY_NAME}} — Completion Rate",
              "metric_chart_metadata": {
                "time_series_display_mode": {},
                "metadata": [
                  {
                    "y_axis": { "description": "Completion Rate", "unit": "PERCENTAGE" },
                    "title": "Completion Rate",
                    "sort_order": "MAX",
                    "connector_export_config": []
                  }
                ]
              }
            }
          }
        },
        {
          "chart_component_layout": {
            "chart_id": { "workflow": { "workflow_id": "{{FUNNEL_WORKFLOW_ID}}", "chart_rule_id": "histogram_key_step" } },
            "layout_settings": { "x": 0, "y": 8, "column_span": 12, "row_span": 4, "is_hidden": false },
            "chart_metadata": {
              "title": "{{KEY_STEP_START}} → {{KEY_STEP_END}} Duration",
              "metric_chart_metadata": {
                "time_series_display_mode": {},
                "metadata": [
                  {
                    "y_axis": { "description": "Duration", "unit": "MILLISECONDS" },
                    "title": "{{KEY_STEP_START}} → {{KEY_STEP_END}} Duration",
                    "sort_order": "MAX",
                    "connector_export_config": []
                  }
                ]
              }
            }
          }
        }
      ],
      "stylistic_components": []
    },
    {
      "name": "Network",
      "charts": [
        {
          "chart_component_layout": {
            "chart_id": { "workflow": { "workflow_id": "{{NETWORK_WORKFLOW_ID}}", "chart_rule_id": "success_rate" } },
            "layout_settings": { "x": 0, "y": 0, "column_span": 12, "row_span": 4, "is_hidden": false },
            "chart_metadata": {
              "title": "{{JOURNEY_NAME}} APIs — Success Rate",
              "metric_chart_metadata": {
                "time_series_display_mode": {},
                "metadata": [
                  {
                    "y_axis": { "description": "Success Rate", "unit": "PERCENTAGE" },
                    "title": "Success Rate",
                    "sort_order": "MAX",
                    "connector_export_config": []
                  }
                ]
              }
            }
          }
        },
        {
          "chart_component_layout": {
            "chart_id": { "workflow": { "workflow_id": "{{NETWORK_WORKFLOW_ID}}", "chart_rule_id": "latency" } },
            "layout_settings": { "x": 0, "y": 4, "column_span": 12, "row_span": 4, "is_hidden": false },
            "chart_metadata": {
              "title": "{{JOURNEY_NAME}} APIs — Latency",
              "metric_chart_metadata": {
                "time_series_display_mode": {},
                "metadata": [
                  {
                    "y_axis": { "description": "Latency", "unit": "MILLISECONDS" },
                    "title": "Latency",
                    "sort_order": "MAX",
                    "connector_export_config": []
                  }
                ]
              }
            }
          }
        },
        {
          "chart_component_layout": {
            "chart_id": { "workflow": { "workflow_id": "{{NETWORK_WORKFLOW_ID}}", "chart_rule_id": "request_count" } },
            "layout_settings": { "x": 0, "y": 8, "column_span": 12, "row_span": 4, "is_hidden": false },
            "chart_metadata": {
              "title": "{{JOURNEY_NAME}} APIs — Request Count",
              "metric_chart_metadata": {
                "time_series_display_mode": {},
                "metadata": [
                  {
                    "y_axis": { "description": "Requests", "unit": "COUNT" },
                    "title": "Request Count",
                    "sort_order": "MAX",
                    "connector_export_config": []
                  }
                ]
              }
            }
          }
        }
      ],
      "stylistic_components": []
    }
  ],
  "dashboard_variables": []
}
```

Omit the Network tab object entirely if Phase 3 was skipped. Add one `name` entry to `funnel_chart_metadata.steps` for each funnel step from Phase 2.

---

## Deploy

```bash
bd dashboard create --request-file cuj-dashboard.json --open
```

`--open` opens the dashboard in the browser immediately. Save the returned dashboard ID for future updates:

```bash
bd dashboard update {{DASHBOARD_ID}} --request-file cuj-dashboard.json --open
```
