# Chart Metadata

Workflow charts have two independent layers of display configuration, both set via companion files
passed to `bd workflow create` or `bd workflow update`:

| File flag | Type | Sets |
|---|---|---|
| `--metadata-file` | `WorkflowMetadata` | Workflow description and title shown above each rule in the workflow graph |
| `--chart-metadata-file` | `PerRuleChartMetadata[]` | Chart title, series labels, and y-axis units |

**Apply both at create time.** Updating `--chart-metadata-file` on a deployed workflow requires one
CLI call per rule (see [Updating after deploy](#updating-after-deploy) below). `--metadata-file`
can always be updated without stopping the workflow.

---

## Workflow metadata (`--metadata-file`)

`PerRuleMetadata.title` sets the label shown above each rule in the workflow graph UI.
Without it, the UI shows the rule ID.

```json
{
  "per_rule_metadata": [
    { "rule_id": "success_rate",  "title": "API Success Rate" },
    { "rule_id": "latency",       "title": "API Latency" },
    { "rule_id": "request_count", "title": "Request Count" }
  ]
}
```

---

## Series labels and y-axis units (`--chart-metadata-file`)

`TimeSeriesMetadata.title` sets the series label shown in chart legends and hover tooltips.
**Without it, the UI falls back to the raw aggregated action ID** — a long opaque hash string.
Always set `TimeSeriesMetadata.title` for any workflow with metric chart rules.

`y_axis.unit` controls the axis label and tooltip formatting.

### Rate / percentage chart

```json
[
  {
    "rule_id": "success_rate",
    "metadata": {
      "title": "API Success Rate",
      "metric_chart_metadata": {
        "time_series_display_mode": {},
        "metadata": [
          {
            "title": "Success Rate",
            "y_axis": { "description": "Success Rate", "unit": "PERCENTAGE" },
            "sort_order": "MAX",
            "connector_export_config": []
          }
        ]
      }
    }
  }
]
```

### Count chart

```json
[
  {
    "rule_id": "request_count",
    "metadata": {
      "title": "Request Count",
      "metric_chart_metadata": {
        "time_series_display_mode": {},
        "metadata": [
          {
            "title": "Request Count",
            "y_axis": { "description": "Requests", "unit": "COUNT" },
            "sort_order": "MAX",
            "connector_export_config": []
          }
        ]
      }
    }
  }
]
```

### Histogram (latency / duration)

Histograms auto-generate one series per percentile (P50, P90, P95, P99, etc.). Use a **single**
`metadata[]` entry — the platform uses `title` as a prefix and appends the percentile suffix.
`"Latency"` renders as `"Latency: P50"`, `"Latency: P90"`, etc.

```json
[
  {
    "rule_id": "latency",
    "metadata": {
      "title": "API Latency",
      "metric_chart_metadata": {
        "time_series_display_mode": {},
        "metadata": [
          {
            "title": "Latency",
            "y_axis": { "description": "Duration", "unit": "MILLISECONDS" },
            "sort_order": "MAX",
            "connector_export_config": []
          }
        ]
      }
    }
  }
]
```

---

## Y-axis unit reference

Pick the unit that matches the data being collected. The full set of valid values:

`PERCENTAGE`, `MILLISECONDS`, `SECONDS`, `MINUTES`, `HOURS`, `DAYS`, `COUNT`, `BYTES`,
`KILOBYTES`, `MEGABYTES`, `GIGABYTES`, `TIMESTAMP`, `UNSPECIFIED`

Use `UNSPECIFIED` only when the metric is truly dimensionless. Avoid leaving it unset — the UI
will show no unit label and tooltip formatting will be incorrect.

---

## Applying at create time

Pass both files alongside `bd workflow create`:

```bash
bd workflow create workflow.json \
  --metadata-file metadata.json \
  --chart-metadata-file chart-metadata.json
```

`chart-metadata.json` can contain multiple entries — one per `metric_chart_rule` in the workflow.

---

## Updating after deploy

`--metadata-file` can always be updated while a workflow is deployed.

`--chart-metadata-file` can also be updated without stopping the workflow, but when `--workflow-file`
is omitted only one `rule_id` entry is accepted per call — pass each rule separately:

```bash
bd workflow update --workflow-id <ID> --chart-metadata-file success-rate.json
bd workflow update --workflow-id <ID> --chart-metadata-file latency.json
bd workflow update --workflow-id <ID> --chart-metadata-file request-count.json
```

To update all rules in one call, stop the workflow first and include `--workflow-file`:

```bash
bd workflow stop <ID>
bd workflow update --workflow-id <ID> \
  --workflow-file workflow.json \
  --chart-metadata-file all-rules.json
bd workflow deploy <ID>
```
