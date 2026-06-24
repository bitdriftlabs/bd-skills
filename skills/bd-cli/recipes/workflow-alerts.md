# Workflow Alerts

Workflow alerts fire when a metric chart breaches a threshold. They attach to a specific time
series (`aggregated_action_id`) within a workflow's chart action. There are two workflow alert
types: **basic** and **SLO**.

> **Not to be confused with Issue Alerts** (`bd issue alert`) which attach to Issue Views and
> support different condition types (event thresholds, rate-of-change, device/session counts).
> See [issue-alerts.md](./issue-alerts.md).

---

## Prerequisites

Before creating alerts, confirm:

1. **A deployed workflow with a metric chart action exists.** If not, create and deploy one first
   (see [workflows.md](./workflows.md)).
2. **You have the workflow ID, chart rule ID, and aggregated action ID.** Extract them:
   ```bash
   bd workflow describe <WORKFLOW_ID> -o json --jq '.workflow.actions[] | {
     rule_id,
     series: [.metric_chart_rule.time_series[] | .aggregated_id]
   }'
   ```
3. **Notification groups exist** (optional but recommended). Alerts without notification groups
   still fire and appear in the alerts UI, but won't route to Slack, PagerDuty, SNS, or Datadog.
   Configure groups first:
   ```bash
   bd notification-group list
   bd notification-group upsert --help
   ```

### Required values to confirm with the user

**For basic alerts:** threshold value, threshold condition (above/below), time window,
consecutive data points, unique devices affected, and optionally notification channels.

**For SLO alerts:** SLO window (error budget period), SLO target (e.g. 99.9%), and optionally
notification channels (global or per-burn-rate-window overrides).

If any required values are missing, prompt the user before proceeding.

### Suggesting thresholds from historical data

When the user asks to add an alert to an existing chart but does not specify a threshold or SLO
target, **analyze the chart data** to suggest reasonable values:

```bash
# Pull the last 7 days of chart data
bd workflow charts <WORKFLOW_ID> -o json --last 7d --jq '.data[].line_data.time_series[] | {
  labels,
  rollup: .aggregated_rollup,
  min: .min,
  max: .max
}'
```

Use the historical baseline to recommend thresholds:
- **Basic alerts:** suggest a warning threshold at ~1.5× the recent steady-state value, critical
  at ~2×, and sustained at ~2.5×. Adjust based on variance — high-variance metrics need wider
  bands to avoid noise.
- **SLO targets:** derive from the observed success rate over 7–30 days. If the metric has been
  at 99.95% for the past 30 days, suggest 99.5% as a conservative target — this gives
  meaningful error budget while still catching real regressions. A tighter target like 99.9%
  is appropriate only when the team has high confidence and wants early warning.

Present suggested values to the user for confirmation. Do not blindly apply them.

**Recommend periodic review:** After creating alerts, suggest to the user that they should
periodically (e.g. monthly or quarterly) have the agent review current thresholds against recent
data to ensure they remain sensible. Thresholds that once made sense can drift — either causing
alert fatigue (too tight) or missing real incidents (too loose) as traffic patterns, baselines, or
product behavior change over time.

---

## UI Limitations

- The workflow UI (`/workflow/<id>`) only shows **one alert** per chart in the advanced settings
  menu. You cannot add additional alerts to a chart via the UI once one exists.
- **All alerts are visible** in the dedicated alerts UI at `/alerting`.
- The CLI has no such limitation — multiple alerts per chart (per `aggregated_action_id`) are
  fully supported. Use the CLI to create multi-alert setups (e.g., warning/critical/sustained
  tiers, or one alert per series on a multi-series chart).

---

## Basic Alerts

A basic alert fires when a metric crosses a threshold within a rolling time window.

### Creating a basic alert

```bash
bd workflow alert upsert <WORKFLOW_ID> <CHART_RULE_ID> <AGGREGATED_ACTION_ID> \
  --name "iOS | Crash Rate | Warning (>0.5%)" \
  --description "Fires when crash rate exceeds 0.5% over a 1h window with 1000+ devices." \
  --type basic \
  --threshold 0.005 \
  --threshold-condition above \
  --basic-window 1h \
  --unique-device-threshold 1000 \
  --notification "group=BitDrift Alerts,min_interval=5m"
```

### Multi-tier escalation pattern

A common pattern for release-gate alerts: warning → critical → sustained, with escalating
device thresholds and consecutive data point requirements.

```bash
# Warning — fires immediately with low device count
bd workflow alert upsert <WF> <RULE> <AGG> \
  --name "iOS | Release Gate | Crash | Warning (>0.5%)" \
  --type basic --threshold 0.005 --threshold-condition above \
  --basic-window 1h --unique-device-threshold 1000 \
  --notification "group=Mobile Alerts,min_interval=5m"

# Critical — requires more devices
bd workflow alert upsert <WF> <RULE> <AGG> \
  --name "iOS | Release Gate | Crash | Critical (>0.75%)" \
  --type basic --threshold 0.0075 --threshold-condition above \
  --basic-window 1h --unique-device-threshold 5000 \
  --notification "group=Mobile Alerts,min_interval=5m"

# Sustained — requires consecutive breaches and high device count
bd workflow alert upsert <WF> <RULE> <AGG> \
  --name "iOS | Release Gate | Crash | Sustained (>1.0%)" \
  --type basic --threshold 0.01 --threshold-condition above \
  --basic-window 1h --consecutive-data-points 3 \
  --unique-device-threshold 10000 \
  --notification "group=Mobile Alerts,min_interval=5m"
```

### Multi-series charts

If a chart has multiple time series (e.g. success rate, 4xx rate, 5xx rate), each series has its
own `aggregated_action_id`. Create separate alerts for each series you want to monitor:

```bash
bd workflow describe <WF> -o json --jq '.workflow.actions[] |
  .metric_chart_rule.time_series[] | .aggregated_id' -r
```

Then upsert one alert per series using the appropriate `aggregated_action_id`.

For user- or agent-created workflows, series typically have names or labels that identify them.
For Instant Insights workflows, series names may be absent — in that case, cross-reference the
`match_id` in each time series against the workflow's `flows` to identify what each series measures:

```bash
bd workflow describe <WF> -o json --jq '.workflow.flows[].steps[].match_rule | {match_id, ootb_match}'
```

### Histogram alerts

For histogram charts (latency distributions), use `--histogram-percentile` to alert on a
specific percentile:

```bash
bd workflow alert upsert <WF> <RULE> <AGG> \
  --name "TTI p95 > 3000ms" \
  --type basic --threshold 3000 --threshold-condition above \
  --basic-window 3600s \
  --histogram-percentile 0.95
```

---

## SLO Alerts

SLO alerts use multi-window multi-burn-rate alerting. They fire when the rate of error budget
consumption indicates the SLO will be breached before the window ends.

### Constraints

- **SLOs can only be created on rate charts that do NOT group (split) by a dimension.** If
  the chart uses `group_by`, you cannot attach an SLO alert. Create a separate ungrouped
  workflow for SLO monitoring if needed.
- Each burn-rate window can route to a different notification group, or they can all share one.

**`slo_duration` only accepts `7d` or `30d`** — the API rejects other values.

### Default burn-rate thresholds

The UI provides these defaults based on the Google SRE Handbook. **The CLI does not offer
defaults** — configure them explicitly:

| Long Window | Short Window | Burn Rate | Error Budget Consumed |
|---|---|---|---|
| 1h | 5min | 16.8 | 10% |
| 6h | 30min | 5.6 | 20% |
| 24h | 2h | 2.8 | 40% |

These represent escalating severity: the 1h/5min window catches fast burns (10% of budget gone
in 1 hour), while the 24h/2h window catches slow sustained degradation (40% consumed over a day).

### Creating an SLO alert

```bash
bd workflow alert upsert <WORKFLOW_ID> <CHART_RULE_ID> <AGGREGATED_ACTION_ID> \
  --name "API Success Rate SLO (99.9% / 30d)" \
  --description "30-day SLO on API success rate. Multi-burn-rate windows per Google SRE handbook." \
  --type slo \
  --slo-duration 30d \
  --slo-target 0.999 \
  --slo-window "short=5m,long=1h,burn=16.8" \
  --slo-window "short=30m,long=6h,burn=5.6" \
  --slo-window "short=2h,long=24h,burn=2.8" \
  --notification "group=SRE On-Call,min_interval=5m"
```

### Per-window notification overrides

Route different burn rates to different channels (e.g. fast-burn pages on-call, slow-burn goes
to Slack). Use `--slo-window-notification` with a 0-based index matching the `--slo-window` order:

```bash
bd workflow alert upsert <WF> <RULE> <AGG> \
  --name "API SLO (99.9% / 30d)" \
  --type slo \
  --slo-duration 30d \
  --slo-target 0.999 \
  --slo-window "short=5m,long=1h,burn=16.8" \
  --slo-window "short=30m,long=6h,burn=5.6" \
  --slo-window "short=2h,long=24h,burn=2.8" \
  --slo-window-notification "0:group=PagerDuty On-Call,min_interval=5m" \
  --slo-window-notification "1:group=SRE Slack,min_interval=15m" \
  --slo-window-notification "2:group=SRE Slack,min_interval=1h"
```

---

## Workflow: Adding Alerts to an Existing Workflow

If the user does not specify a workflow, **ask first** rather than searching speculatively:
- Do you have a specific workflow in mind (name or ID)?
- Would you like to create a new workflow for this?
- Or would you like me to search for a workflow that might match?

Once you have a workflow ID:

1. **Describe the workflow** to get the chart rule ID and aggregated action ID(s):
   ```bash
   bd workflow describe <WF> -o json --jq '.workflow.actions[] | {
     rule_id, series: [.metric_chart_rule.time_series[] | .aggregated_id]
   }'
   ```
2. **Check existing alerts** on that chart:
   ```bash
   bd workflow alert config <WF> <CHART_RULE_ID> -o json
   ```
3. **Confirm required values with the user** (see Prerequisites above).
4. **Create the alert(s)** using `bd workflow alert upsert`.

## Workflow: Creating a New Workflow + Alerts

1. **Create and deploy the workflow** (see [workflows.md](./workflows.md)).
2. **Wait for deployment** — **never attempt to attach an alert until the workflow status is `LIVE`.** Attaching to a non-live workflow will fail.
3. **Extract IDs** from the deployed workflow:
   ```bash
   bd workflow describe <NEW_WF_ID> -o json --jq '.workflow.actions[] | {
     rule_id, series: [.metric_chart_rule.time_series[] | .aggregated_id]
   }'
   ```
4. **Confirm required values with the user.**
5. **Create the alert(s).**

---

## Pitfalls

- **Threshold units:** Rate charts display percentages but alert thresholds use raw decimals.
  0.05 = 5%, not 0.05%.
- **SLO + group_by incompatibility:** If you need both version-level breakdown and SLO alerting,
  create two separate workflows — one grouped for visibility, one ungrouped for the SLO.
- **Notification groups must exist first.** If you reference a group name that doesn't exist,
  the upsert will fail. List available groups with `bd notification-group list`.
- **Updating an alert replaces the full config.** Pass `--id` to update an existing alert; omit
  it to create a new one. Either way, all desired field values must be re-specified — omitted
  fields are cleared. Use `--delete` to remove an alert entirely.
