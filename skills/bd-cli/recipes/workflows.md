# Workflow Lifecycle

This recipe covers creating, deploying, updating, and managing workflows. For the proto schema and match rule reference, see [workflow-schema.md](../reference/workflow-schema.md).

---

## Choose the right mode first

Before deploying anything, decide which kind of help the user needs:

### Active investigation

Use this path when the user is debugging an issue that is happening now or very recently and wants
to understand real user impact, inspect a concrete session, or confirm a suspected regression.

- Prefer **existing evidence** first: Instant Insights, issue groups, existing captured sessions,
  and already-deployed workflows.
- When looking for an applicable existing workflow, use the workflow description in metadata to
  identify what the workflow is intended to detect, measure, or capture and why it was created.
- Only deploy a new `flush_rule` workflow if existing data cannot answer the question.
- Before deploying live capture, confirm the target behavior is still occurring in the current
  window. Live capture only observes **new** sessions after deployment.

### Ongoing data collection

Use this path when the user wants durable measurement over time: funnels, adoption, long-running
comparisons, cohort analysis, or persistent monitoring.

- Treat the task as workflow design, not incident response.
- Optimize for signal quality, grouping, aggregation, and the right time horizon.
- Session capture may still be useful, but it is not the default.

If timing is unclear, determine that first. Do not assume a 24h aggregate means the issue is still
active right now.

---

## Choose workflow granularity deliberately

Use **one workflow for one analytic question or one coherent flow**. If the user is really asking
about several related but distinct signals, prefer multiple workflows rather than one large
catch-all workflow.

Split into multiple workflows when:

- the entry points represent different user journeys
- different teams would reason about the results independently
- the outputs are better compared side by side than merged into one workflow definition
- the workflow has grown into a presentation artifact instead of a measurement artifact

When the goal is a multi-panel operational view, build multiple focused workflows and compose their
charts into a dashboard. Do not use workflow complexity as a substitute for dashboard composition.

Large multi-entry workflows are still valid when the entries truly form one shared funnel or one
tightly related measurement problem, but examples like a 14-entry-point operational board should be
treated as a smell and revisited first.

---

## Creating a Workflow

Use `bd workflow create --help` for the command shape and `bd schema workflow.create` for the file
inputs and JSON types.

The workflow payload itself lives in `Workflow`. The optional companion files serve different
purposes:

- `--metadata-file` sets workflow metadata such as description and per-rule panel titles
- `--chart-metadata-file` sets per-series chart metadata such as legend labels

**`--chart-metadata-file`** sets series labels and y-axis units. Without it, charts fall back to raw aggregated action IDs as series labels. **`--metadata-file`** sets the panel title shown above each rule in the workflow graph. See [chart-metadata.md](./chart-metadata.md) for formats, unit reference, histogram prefix behavior, and update patterns.

When creating a workflow, set the workflow description in metadata (typically via
`--metadata-file`). Use it to explain the workflow's purpose: what it is trying to measure,
detect, or capture, and, critically, why this workflow is being created at all (for example,
to investigate a suspected regression, monitor adoption, or validate a hypothesis). Focus on capturing
the intent over describing what the workflow does as this can be inferred from the configuration.

## Network path fields: `_path` vs `_path_template`

These two fields serve different purposes and must not be swapped:

| Field | What it contains | Use it for |
|---|---|---|
| `_path` | The actual request path (e.g. `/api/v1/user/12345`) | Matcher conditions |
| `_path_template` | Normalized form with variable segments collapsed (e.g. `/api/v1/user/<id>`) | `group_by_fields` |

**Matching:** always use `_path` in `base_matcher` conditions.
- Static path (no variable segments): `"operator": "EQUAL", "string_value": "/api/v1/graphql"`
- Dynamic path (contains IDs or other variable segments): `"operator": "REGEX", "string_value": "/api/v1/user/.*"`

**Grouping:** use `_path_template` in `group_by_fields` at the top-level `Workflow` object so charts show one series per endpoint pattern rather than one series per unique path.

```json
{
  "name": "...",
  "flows": [...],
  "actions": [...],
  "group_by_fields": ["_path_template"]
}
```

Note: `group_by_fields` lives in the top-level `Workflow` JSON, not in `--chart-metadata-file`.

**`or_matcher` warning:** do not use `or_matcher` as the root of `generic_match` inside an `ootb_match`. The API accepts it but the workflow page fails to render in the UI. Always use `and_matcher` at the root, with `or_matcher` nested inside for multi-value conditions on a single field.

---

## Organizing workflows with tags

Use workflow tags to organize related workflows after the workflow boundaries are already sound.
Tags help with discovery and saved workflow views, but they do **not** fix a workflow that should
really be split apart.

```bash
bd workflow tag list
bd workflow tag set <WORKFLOW_ID> --tag payments --tag critical
```

`bd workflow tag set` replaces the entire tag set for the workflow. Re-specify every tag you want
to keep.

## Naming Chart Series

**Any metric chart with more than one time series will show raw `aggregated_id` hashes as series
labels unless chart metadata is explicitly provided.** Always supply a `--chart-metadata-file` when
deploying a workflow whose `metric_chart_rule` has multiple time series.

The `TimeSeriesMetadata[]` array inside `MetricChartMetadata` maps **positionally** to the time
series in the workflow — `metadata[0].title` names `time_series[0]`, and so on.

```json
[
  {
    "rule_id": "my_count_chart",
    "metadata": {
      "title": "Requests by Step",
      "metric_chart_metadata": {
        "time_series_display_mode": {},
        "metadata": [
          { "y_axis": { "description": "Requests", "unit": "COUNT" }, "title": "Step 1", "sort_order": "MAX", "connector_export_config": [] },
          { "y_axis": { "description": "Requests", "unit": "COUNT" }, "title": "Step 2", "sort_order": "MAX", "connector_export_config": [] },
          { "y_axis": { "description": "Requests", "unit": "COUNT" }, "title": "Step 3", "sort_order": "MAX", "connector_export_config": [] }
        ]
      }
    }
  }
]
```

Apply with:

```bash
bd workflow update --workflow-id <ID> --chart-metadata-file chart-metadata.json
```

This can be done after deployment without stopping the workflow.

---

## Updating a Workflow

Use `bd workflow update --help` for the accepted flags and `bd schema workflow.update` for the file
inputs.

The durable workflow-level rule is: **stop deployed workflows before editing workflow logic.**
Metadata and chart metadata can be updated independently of the workflow graph.

If the workflow has active alerts, you must delete them before stopping and editing. See
[Updating a Workflow with Active Alerts](#updating-a-workflow-with-active-alerts) below.

When updating a workflow, also update the description in metadata if the workflow's purpose, scope,
or reason for existing has changed. Keep the description aligned with both what the workflow does
and, if relevant, why the team is running it.

## Updating a Workflow with Active Alerts

A workflow with an active alert cannot have its logic edited. The UI shows "This Workflow has an active alert. Please delete the alert to make changes." The same constraint applies via CLI. The pattern is: capture → delete → stop → update → deploy → re-create.

**Before starting:** consider whether the workflow change affects the alert's semantics. If you're changing a matcher, threshold source, or flow structure, the existing alert config may no longer be correct — not just stale. Review the alert name, threshold, and target series against the updated workflow before blindly re-applying the backup.

### 1. Capture the alert config

```bash
bd workflow alert config <WORKFLOW_ID> <CHART_RULE_ID> -o json > alert-backup.json
```

Note the `id`, `aggregated_action_id`, and `alert_type` from the output.

### 2. Delete the alert

```bash
bd workflow alert upsert <WORKFLOW_ID> <CHART_RULE_ID> <AGGREGATED_ACTION_ID> \
  --id <ALERT_ID> --delete
```

### 3. Stop, update, and redeploy the workflow

```bash
bd workflow stop <WORKFLOW_ID>
bd workflow update --workflow-id <WORKFLOW_ID> --workflow-file updated.json
bd workflow deploy <WORKFLOW_ID>
```

### 4. Fetch the new aggregated_action_id

> **Critical:** Updating workflow logic changes every `aggregated_id` in the workflow. The ID captured in step 1 is now stale. Do not use it to recreate the alert — it will cause "No Data Found Yet" in the alert UI even though the workflow is producing data.

After redeploying, fetch the current aggregated_action_id for each rule that had an alert:

```bash
bd workflow describe <WORKFLOW_ID> -o json \
  --jq '.workflow.actions[] | select(.rule_id == "<CHART_RULE_ID>") | .metric_chart_rule.time_series[].aggregated_id'
```

Use the value returned here (not the one from step 1) in the `bd workflow alert upsert` call below.

### 5. Re-create the alert

Use `bd workflow alert upsert` without `--id` to create a new alert. Translate the captured JSON back to CLI flags:

> `bd workflow alert upsert` does not support `--request-file`, so the JSON backup cannot be passed directly. You must translate the fields to CLI flags using the tables below.

**SLO alert fields:**

| JSON field | CLI flag |
|---|---|
| `common_config.name` | `--name` |
| `common_config.description` | `--description` |
| `slo_alert.slo_duration` | `--slo-duration` (convert from seconds) |
| `slo_alert.slo_target` | `--slo-target` |
| `slo_alert.window_and_burn_rates[]` | `--slo-window short=X,long=Y,burn=Z` (one flag per window) |

**Basic alert fields:**

| JSON field | CLI flag |
|---|---|
| `basic_alert.threshold` | `--threshold` |
| `basic_alert.condition` | `--threshold-condition above\|below` |
| `basic_alert.window` | `--basic-window` (convert from seconds) |
| `basic_alert.histogram_configuration.percentile` | `--histogram-percentile` |

**Duration conversion** — proto encodes as `"Xs"` (e.g. `"300.000000000s"`); strip the `.000000000s` and divide:

| Seconds | CLI value |
|---|---|
| 300 | `5m` |
| 1800 | `30m` |
| 3600 | `1h` |
| 7200 | `2h` |
| 21600 | `6h` |
| 86400 | `24h` |
| 2592000 | `30d` |

Example re-create for a 30-day SLO with MWMBR windows:

```bash
bd workflow alert upsert <WORKFLOW_ID> <CHART_RULE_ID> <AGGREGATED_ACTION_ID> \
  --type slo \
  --name "My SLO Alert" \
  --slo-duration 30d \
  --slo-target 0.99 \
  --slo-window short=5m,long=1h,burn=16.8 \
  --slo-window short=30m,long=6h,burn=5.6 \
  --slo-window short=2h,long=24h,burn=2.8 \
  --notification group=<GROUP_NAME>
```

---

## Using `describe` as a Template

`bd workflow describe <id> -o json` returns the full workflow proto. To use it as a create/update
template, **strip server-managed fields first.** Check `bd schema workflow.create Workflow --docs`
and remove any field documented as server-generated or immutable, even if an older example still
shows it.

## Deploy-and-Wait Pattern

Use this pattern for **active investigations** when the user needs fresh sessions from a condition
that is still happening now.

1. **Confirm current activity** — before deploying, verify the target phenomenon is still present
   in the recent window. For example: recent requests for an endpoint, fresh crashes, or a current
   latency spike.
2. **Deploy** — create with a `flush_rule` triggered by the condition.
3. **Set a temporary lifetime** — use `deployment_expiration` for investigative workflows unless
   the user explicitly wants a durable workflow.
4. **Poll** — check `bd workflow captured-sessions <id> -o json --last 24h` periodically. An empty
   result means no matching sessions yet — not necessarily an error.
5. **Branch on no hits** — distinguish between no current traffic, no current failures, propagation
   delay, and an overly narrow match before broadening the workflow.
6. **Iterate** — if needed, lower the threshold, broaden the match, or verify that the SDK is
   active on the target devices.

Do **not** use this pattern to recover historical sessions that happened before the workflow was
deployed. If the user needs past evidence, prefer issues, existing sessions, or already-captured
workflow data.

---

## VIP / Known Entity Capture

Use this pattern when the user wants **guaranteed session capture for specific users** — customer support escalations, executives, internal testers, or high-value accounts.

### Prerequisites

1. The app calls `setEntityID` / `setEntityId` with the user's identifier (iOS/Android SDK 0.23.0+)
2. The entity has been bookmarked in the bitdrift UI, or created via `bd entity known upsert <entity_id> --display-name "Name"`

### Why this beats the old field-match workaround

The previous approach was to deploy a `generic_match` workflow filtering on a `user_id` field. That workflow deployed to **every device in the fleet** and matched on each one — wasteful and noisy. `known_entity_match` is evaluated against the server-managed known-entity set, so it only fires for bookmarked entities.

### Workflow JSON

```json
{
  "flows": [
    {
      "exclusive": {},
      "steps": [
        {
          "match_rule": {
            "match_id": "vip-session",
            "known_entity_match": {}
          }
        }
      ],
      "action_rules": [
        {
          "rule_id": "capture-vip",
          "flush_rule": {
            "match_id": "vip-session"
          }
        }
      ]
    }
  ]
}
```

Deploy with `bd workflow create --workflow-file <file>` then `bd workflow deploy <id>`. No `deployment_expiration` — this should be a durable workflow that covers all current and future bookmarked entities automatically.
