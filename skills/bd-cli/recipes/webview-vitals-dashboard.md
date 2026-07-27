# Webview Web Vitals Dashboard

A curated set of 29 workflows covering Google Core Web Vitals, page load lifecycle, errors,
network performance, and engagement for Android webviews instrumented with the bitdrift Capture
SDK. Use this whenever a customer asks for webview monitoring, wants to track CWV against Google
thresholds, or needs an SLO on webview performance.

**Android only.** Requires Capture SDK v0.22.3+ with `WebViewConfiguration` configured on the
app. Different flags enable different data — see the [Configuration options](#configuration-options)
section. Templates are in `webview-vitals-dashboard/templates/`, with matching chart metadata
(title, series label, y-axis unit — see [chart-metadata.md](./chart-metadata.md)) in
`webview-vitals-dashboard/chart-metadata/`, one file per slug.

---

## Configuration options

The customer must enable the relevant flags in `WebViewConfiguration`. Match which workflows to
deploy against what they have enabled:

| Flag | Workflows it enables |
|---|---|
| `captureWebVitals = true` | All `lcp-*`, `fcp-*`, `inp-*`, `ttfb-*`, `cls-*` workflows |
| `capturePageViews = true` | `page-view-duration` |
| `captureNavigationEvents = true` | `page-load-time`, `dom-content-loaded` |
| `captureLongTasks = true` | `long-tasks` |
| `captureConsoleLogs = true` | `console-logs` |
| `captureErrors = true` | `webview-errors`, `resource-errors` |
| `captureUserInteractions = true` | `webview-user-interactions` |
| `captureNetworkRequests = true` | All `webview-http-*` workflows |

`webview-initialized` and `webview-not-initialized` are emitted regardless of configuration flags —
they reflect whether the SDK itself initialized correctly.

---

## Deploy

### 1. Confirm inputs

Ask the customer for their Android app bundle ID(s). All templates set `platform_targets` to
`[{"android": {"apps": []}}]` (all Android apps) by default. Only deploy workflows for features
the customer has enabled.

### 2. Create and deploy each workflow

Scope each workflow to the target app(s) with `--app-id`/`--platform` on `create` — no manual
template editing needed. Always pass the matching `--chart-metadata-file` too — without it the
workflow has no native chart title, series label, or y-axis unit, and "Display properties" in the
UI shows blank even if a dashboard built on top of it happens to show its own override title:

```bash
bd auth   # authenticate against the target tenant

# For each workflow:
bd workflow create templates/<slug>.json --app-id <ANDROID_APP_ID> --platform android \
  --chart-metadata-file chart-metadata/<slug>.json \
  -o json --jq '.id' -r
# → prints <WORKFLOW_ID>
bd workflow deploy <WORKFLOW_ID>
```

Repeat `--app-id` for multiple apps, and repeat the whole create+deploy step for every workflow
the customer has enabled. If the customer explicitly wants this applied to every Android app in
the tenant, omit `--app-id`/`--platform` and create from the template as-is. The `bd workflow
deploy` call is idempotent — re-running it on an already-LIVE workflow is safe.

**Rate limits:** sleep 2–3s between `bd` calls if you hit `code: 8, message: public API rate limited`.
If limits persist, wait and retry later (or contact bitdrift support).

### 3. Wait for LIVE

```bash
bd workflow describe <WORKFLOW_ID> -o json --jq '.workflow.state' -r
```

The workflow must reach `LIVE` state before attaching alerts. Poll until it does.

### 4. Attach alerts

See alert specs in the [Workflow inventory](#workflow-inventory) section below. Use
`bd workflow alert upsert` with `--type basic` for count/histogram alerts and `--type slo` for
good-rate SLO workflows.

For Core Web Vitals histogram alerts (LCP, FCP, INP, TTFB, CLS), evaluate at **p75** — this
matches Google's CWV assessment methodology, which classifies good/needs-improvement/poor based on
the 75th percentile, not p90/p95. Use the same `--histogram-percentile 0.75` for both the warning
and critical alert on a given metric; only the `--threshold` differs between the two:

```bash
bd workflow alert upsert <WORKFLOW_ID> <CHART_RULE_ID> <AGG_ID> \
  --name "<name>" --type basic \
  --threshold <value> --threshold-condition above \
  --basic-window 1h --histogram-percentile 0.75 \
  --unique-device-threshold 50 -o json
```

For non-CWV histogram alerts (page load lifecycle, long tasks, engagement), the existing p90/p95
two-tier convention still applies — see the [Workflow inventory](#workflow-inventory) tables below
for which percentile each alert uses (same `--histogram-percentile` flag, just a different value).

For SLO alerts (good-rate workflows), `--type slo` requires at least one `--slo-window`. Use the
three multi-burn-rate windows from the [SLO Good-Rate Workflows](#slo-good-rate-workflows) table:

```bash
bd workflow alert upsert <WORKFLOW_ID> <CHART_RULE_ID> <AGG_ID> \
  --name "<name>" --type slo \
  --slo-target 0.90 --slo-duration 30d \
  --slo-window short=5m,long=1h,burn=16.8 \
  --slo-window short=30m,long=6h,burn=5.6 \
  --slo-window short=2h,long=24h,burn=2.8 \
  --unique-device-threshold 50 -o json
```

To find `<CHART_RULE_ID>` and `<AGG_ID>`:
```bash
bd workflow describe <WORKFLOW_ID> -o json --jq \
  '[.workflow.actions[] | {rule_id: .rule_id, agg_id: .metric_chart_rule.time_series[].aggregated_id}]'
```

### 5. Create a dashboard

Once all workflows are LIVE, group them into a dashboard:
```bash
bd dashboard create --request-file <dashboard.json> --open
```

Use `bd schema dashboard.create UpsertCustomDashboardRequest --depth 2` for the payload shape.
Suggested section groupings: Core Web Vitals — By Version, Core Web Vitals — By URL, Visual
Stability, Page Load Lifecycle, Errors & Diagnostics, Network, SLO Good-Rate.

---

## Workflow inventory

### Core Web Vitals — by App Version
Histogram of `_value` (ms) by `app_version`. Use for release regression detection. Alerts are
evaluated at **p75**, matching Google's CWV good/needs-improvement/poor methodology.

| Slug | Metric | p75 warning (needs improvement) | p75 critical (poor) |
|---|---|---|---|
| `lcp-by-version` | LCP | > 2500ms | > 4000ms |
| `fcp-by-version` | FCP | > 1800ms | > 3000ms |
| `inp-by-version` | INP | > 200ms | > 500ms |
| `ttfb-by-version` | TTFB | > 800ms | > 1800ms |

### Core Web Vitals — by URL
Same match, grouped by `_page_url`. Use for identifying which pages are degraded. Alerts evaluated
at **p75**, same as the by-version tables.

| Slug | Metric | p75 warning (needs improvement) | p75 critical (poor) |
|---|---|---|---|
| `lcp-by-url` | LCP | > 2500ms | > 4000ms |
| `fcp-by-url` | FCP | > 1800ms | > 3000ms |
| `inp-by-url` | INP | > 200ms | > 500ms |
| `ttfb-by-url` | TTFB | > 800ms | > 1800ms |

### Visual Stability (CLS)
CLS is a ratio score (0–1+, good < 0.1). Logged as a UX log, not a span.

| Slug | Chart | Alert |
|---|---|---|
| `cls-by-rating` | Count by `_rating` (good/needs-improvement/poor) | None |
| `cls-by-url` | Histogram by `_page_url` | p75 > 0.1 warning, p75 > 0.25 critical |
| `cls-good-rate` | Good-rate SLO | 90% / 30d |

### Page Load Lifecycle
Matches `webview.lifecycle` events. Field: `_performance_time` (ms).

| Slug | Event | p90 warning | p95 critical |
|---|---|---|---|
| `page-load-time` | `load` | > 3000ms | > 6000ms |
| `dom-content-loaded` | `DOMContentLoaded` | > 1500ms | > 3000ms |

### Engagement

| Slug | Chart | Alert |
|---|---|---|
| `page-view-duration` | Histogram of `_duration_ms` by `_url` | p90 > 30s, p95 > 60s |
| `webview-user-interactions` | Count by `_interaction_type` + `_tag_name` | None |

### Errors & Diagnostics
Alert thresholds are volume-dependent — configure per customer after establishing a baseline.

| Slug | Chart | Alert |
|---|---|---|
| `webview-errors` | Count by `_message` + `log_level` | None |
| `resource-errors` | Count by `log_level` | None |
| `long-tasks` | Histogram of `_duration_ms` by `app_version` | p95 > 150ms, p99 > 300ms |
| `console-logs` | Count by `log_level` | None |
| `webview-initialized` | Count by `app_version` | None |
| `webview-not-initialized` | Count by `reason` + `app_version` | Count > 10/1h warning, > 100/1h critical |

### Webview Network
Requires `captureNetworkRequests = true` in `WebViewConfiguration`.

| Slug | Chart | Alert |
|---|---|---|
| `webview-http-latency` | Histogram of `_duration_ms` by `_host` | p90 > 1000ms, p95 > 3000ms |
| `webview-http-errors` | Count by `_host` + `_status_code` (failed only) | None |
| `webview-http-by-type` | Count by `_request_type` | None |
| `webview-http-success-rate` | Success rate (SLO workflow) | 95% / 30d |

### SLO Good-Rate Workflows
Ungrouped rate charts for SLO alerting with three multi-burn-rate windows:

| Window | Burn rate | Budget consumed |
|---|---|---|
| 1h long / 5m short | 16.8x | 10% in 1h — fast burn |
| 6h long / 30m short | 5.6x | 20% in 6h — medium burn |
| 24h long / 2h short | 2.8x | 40% in 24h — slow creep |

| Slug | SLO target |
|---|---|
| `lcp-good-rate`, `fcp-good-rate`, `inp-good-rate`, `ttfb-good-rate`, `cls-good-rate` | 90% / 30d |
| `webview-http-success-rate` | 95% / 30d |

---

## Match patterns

For reference when authoring custom variants. See
[reference/webview-fields.md](../reference/webview-fields.md) for the full field inventory.

| Log type | Match |
|---|---|
| Web vital spans (LCP/FCP/INP/TTFB) | `_source == "webview"` AND `_span_type == "end"` AND `_metric == "<METRIC>"` |
| CLS (UX log, not span) | `_source == "webview"` AND `message == "webview.webVital"` AND `_metric == "CLS"` |
| Lifecycle events | `_source == "webview"` AND `message == "webview.lifecycle"` AND `_event == "<EVENT>"` |
| Page view spans | `_source == "webview"` AND `_span_name == "webview.pageView"` AND `_span_type == "end"` |
| Long tasks | `_source == "webview"` AND `message == "webview.longTask"` |
| JS errors | `_source == "webview"` AND `message == "webview.error"` |
| Resource errors | `_source == "webview"` AND `message == "webview.resourceError"` |
| Console logs | `_source == "webview"` AND `message == "webview.console"` |
| User interactions | `_source == "webview"` AND `message == "webview.userInteraction"` |
| HTTP spans | `_source == "webview"` AND `_span_name == "_http"` AND `_span_type == "end"` |
| SDK initialized | `_source == "webview"` AND `message == "webview.initialized"` |
| SDK not initialized | `_source == "webview"` AND `message == "webview.notInitialized"` |
