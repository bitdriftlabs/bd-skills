# Phase 4: Alerts

> For full alert CLI syntax, flag reference, and pitfalls, see the workflow-alerts recipe in `$bd-cli`.

Two alerts to create:

1. **Completion rate SLO** — multi-window multi-burn-rate alert on the ungrouped completion rate workflow from Phase 2
2. **Key step p95 alert** — basic histogram percentile alert on the histogram rule in the funnel workflow from Phase 2

**Prerequisite:** both the completion rate and funnel workflows must be `LIVE` before attaching alerts. Verify:

```bash
bd workflow describe {{COMPLETION_RATE_WORKFLOW_ID}} -o json --jq '.workflow.state'
bd workflow describe {{FUNNEL_WORKFLOW_ID}} -o json --jq '.workflow.state'
```

**Prerequisite:** check that at least one notification group exists before creating alerts:

```bash
bd notification-group list
```

If the list is empty, pause and tell the user: "No notification groups are configured — alerts will fire but go nowhere. Please create one in the portal before continuing, or confirm you'd like to proceed without notification routing."

---

## Extract IDs

For each workflow, get the chart rule ID and aggregated action ID needed by `bd workflow alert upsert`:

```bash
bd workflow describe {{WORKFLOW_ID}} -o json --jq '.workflow.actions[] | {rule_id, series: [.metric_chart_rule.time_series[]? | .aggregated_id]}'
```

The `[]?` operator suppresses errors on non-chart actions (e.g. `measure_time_rule`, `flush_rule`) that have no `time_series`.

---

## Alert 1: Completion Rate SLO

Before creating, suggest a target from historical data:

```bash
bd workflow charts {{COMPLETION_RATE_WORKFLOW_ID}} -o json --last 30d \
  --jq '.data[].line_data.time_series[] | {min: .min, rollup: .aggregated_rollup}'
```

Present the 30-day baseline to the user and suggest a conservative target (e.g. if observed rate is 94%, suggest 90% to start). If the workflow was recently deployed and has no data, use 0.90 as the starting default and note it should be revisited once 30 days of data have accumulated.

The three burn-rate windows follow the Google SRE Handbook — configure all three explicitly (the CLI has no defaults):

```bash
bd workflow alert upsert {{COMPLETION_RATE_WORKFLOW_ID}} {{CHART_RULE_ID}} {{AGGREGATED_ACTION_ID}} \
  --name "{{JOURNEY_NAME}} — Completion Rate SLO ({{TARGET}}% / 30d)" \
  --description "30-day SLO on journey completion rate. MWMBR per Google SRE Handbook." \
  --type slo \
  --slo-duration 30d \
  --slo-target {{TARGET_DECIMAL}} \
  --slo-window "short=5m,long=1h,burn=16.8" \
  --slo-window "short=30m,long=6h,burn=5.6" \
  --slo-window "short=2h,long=24h,burn=2.8" \
  --notification "group={{NOTIFICATION_GROUP}},min_interval=5m"
```

`--slo-duration` only accepts `7d` or `30d`. `--slo-target` is a decimal (0.90 = 90%).

If the completion rate workflow only has a failure-count metric (no success-rate chart), use
`--slo-rate-type failure-rate` and enter the failure-rate target directly instead of computing
`1 - rate` by hand — see [Failure-rate SLOs](../../bd-cli/recipes/workflow-alerts.md#failure-rate-slos)
in the workflow-alerts recipe.

---

## Alert 2: Key Step p95

The p95 alert targets the `histogram_key_step` rule in the funnel workflow from Phase 2.

Before creating, check if 7 days of histogram data is available:

```bash
bd workflow charts {{FUNNEL_WORKFLOW_ID}} -o json --last 7d \
  --jq '[.data[] | select(.chart_id.workflow.chart_rule_id == "histogram_key_step") | .line_data.time_series[] | {rollup: .aggregated_rollup, max: .max}]'
```

If data is available, suggest a threshold at ~1.5× the observed p95. If not yet available, ask the user to provide an estimate or defer this alert until data accumulates.

Once you have a threshold, update the funnel workflow's slow session capture condition to match:

```bash
# Note the threshold for use when updating the session capture condition
# threshold_ms: {{THRESHOLD_MS}}  →  threshold_s: {{THRESHOLD_MS / 1000}}s
```

Then create the alert:

```bash
bd workflow alert upsert {{FUNNEL_WORKFLOW_ID}} histogram_key_step {{AGGREGATED_ACTION_ID}} \
  --name "{{JOURNEY_NAME}} — {{KEY_STEP_START}} → {{KEY_STEP_END}} p95 > {{THRESHOLD_MS}}ms" \
  --type basic \
  --threshold {{THRESHOLD_MS}} \
  --threshold-condition above \
  --basic-window 1h \
  --histogram-percentile 0.95 \
  --notification "group={{NOTIFICATION_GROUP}},min_interval=15m"
```

After the alert is created, update the funnel workflow to apply the confirmed p95 threshold to the session capture condition. Use `bd workflow update --editor` to open the workflow and update `slow_key_step.measure_time_condition.duration_threshold` to `"{{THRESHOLD_S}}s"`.

---

## Gate

Report: alert IDs for both alerts.

Then ask: "Ready to continue to Phase 5 — Dashboard?"
