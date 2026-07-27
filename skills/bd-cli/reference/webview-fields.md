# Webview Log Fields

Field reference for logs emitted by the bitdrift Android WebView integration (Capture SDK
v0.22.3+). All webview logs carry `_source == "webview"`. Use this reference when authoring
workflow match rules, group-by fields, or timeline search filters against webview data.

For a ready-made set of workflows covering all these log types, see
[recipes/webview-vitals-dashboard.md](../recipes/webview-vitals-dashboard.md).

---

## Common fields (all webview logs)

| Field | Value | Notes |
|---|---|---|
| `_source` | `"webview"` | Present on every webview log — always include in match rules |
| `app_version` | e.g. `"1.2.3"` | Native app version, inherited from the SDK session |

---

## Web vital spans (LCP, FCP, INP, TTFB)

Emitted as span-end events when each metric is recorded.

**Match:** `_source == "webview"` AND `_span_type == "end"` AND `_metric == "<METRIC>"`

Note: `message` is empty on these spans — do not match on `message`.

| Field | Example | Notes |
|---|---|---|
| `_span_type` | `"end"` | Always `"end"` for recorded vitals |
| `_span_name` | `"webview.webVital"` | Span name for all CWV except CLS |
| `_metric` | `"LCP"`, `"FCP"`, `"INP"`, `"TTFB"` | Identifies which vital |
| `_value` | `1234.5` | Metric value in milliseconds |
| `_page_url` | `"https://example.com/checkout"` | Page URL where the vital was recorded |
| `_rating` | `"good"`, `"needs-improvement"`, `"poor"` | Google CWV rating bucket |

**Good thresholds:** LCP < 2500ms, FCP < 1800ms, INP < 200ms, TTFB < 800ms.

---

## CLS (Cumulative Layout Shift)

CLS is logged as a UX log, **not a span** — no `_span_type` field.

**Match:** `_source == "webview"` AND `message == "webview.webVital"` AND `_metric == "CLS"`

| Field | Example | Notes |
|---|---|---|
| `message` | `"webview.webVital"` | |
| `_metric` | `"CLS"` | |
| `_value` | `0.12` | Dimensionless score (good < 0.1, poor > 0.25) |
| `_page_url` | `"https://example.com/checkout"` | |
| `_rating` | `"good"`, `"needs-improvement"`, `"poor"` | |

---

## Page view spans

Emitted when the user navigates to a new page within the webview (SPA navigation or full load).

**Match:** `_source == "webview"` AND `_span_name == "webview.pageView"` AND `_span_type == "end"`

| Field | Example | Notes |
|---|---|---|
| `_span_name` | `"webview.pageView"` | |
| `_span_type` | `"end"` | |
| `_url` | `"https://example.com/checkout"` | Use `_url` here, not `_page_url` |
| `_duration_ms` | `4521.0` | Time on page in milliseconds |

---

## Lifecycle events

Emitted for browser lifecycle transitions. Field: `_event` identifies the specific event.

**Match:** `_source == "webview"` AND `message == "webview.lifecycle"` AND `_event == "<EVENT>"`

| `_event` value | Meaning | Key field |
|---|---|---|
| `"load"` | Page fully loaded | `_performance_time` (ms since navigation start) |
| `"DOMContentLoaded"` | DOM parsed and ready | `_performance_time` (ms since navigation start) |
| `"visibilitychange"` | Tab visibility changed | (no additional value fields) |

| Field | Example | Notes |
|---|---|---|
| `message` | `"webview.lifecycle"` | |
| `_event` | `"load"` | Differentiates event types — do not use `log_body` for this |
| `_performance_time` | `2100.0` | Time in ms since navigation start |

---

## Long tasks

Emitted for main-thread tasks that block for > 50ms.

**Match:** `_source == "webview"` AND `message == "webview.longTask"`

| Field | Example | Notes |
|---|---|---|
| `message` | `"webview.longTask"` | |
| `_duration_ms` | `234.0` | Task duration in milliseconds |

---

## JS errors and promise rejections

**Match:** `_source == "webview"` AND `message == "webview.error"`

| Field | Example | Notes |
|---|---|---|
| `message` | `"webview.error"` | |
| `_message` | `"TypeError: Cannot read..."` | The error message text |
| `log_level` | `"error"` | |

---

## Resource errors

Failed resource loads (images, scripts, CSS, fonts).

**Match:** `_source == "webview"` AND `message == "webview.resourceError"`

| Field | Example | Notes |
|---|---|---|
| `message` | `"webview.resourceError"` | |
| `log_level` | `"warning"`, `"error"` | |

---

## Console logs

JavaScript `console.log/warn/error/info` output.

**Match:** `_source == "webview"` AND `message == "webview.console"`

| Field | Example | Notes |
|---|---|---|
| `message` | `"webview.console"` | |
| `log_level` | `"info"`, `"warning"`, `"error"` | Maps from JS `console.*` method |
| `_message` | `"Checkout initialized"` | The console message text |

---

## User interactions

Tap and click events, including rage clicks.

**Match:** `_source == "webview"` AND `message == "webview.userInteraction"`

| Field | Example | Notes |
|---|---|---|
| `message` | `"webview.userInteraction"` | |
| `_interaction_type` | `"click"`, `"rage_click"` | Type of interaction |
| `_tag_name` | `"button"`, `"a"`, `"div"` | HTML element type |
| `_class_name` | `"btn-primary"` | CSS class(es) on the element |
| `_text_content` | `"Add to cart"` | Visible text of the element |
| `_is_clickable` | `"true"`, `"false"` | Whether the element has a click handler |

---

## HTTP network spans

Emitted for each outbound HTTP request made from the webview. Requires
`captureNetworkRequests = true` in `WebViewConfiguration`.

**Match:** `_source == "webview"` AND `_span_name == "_http"` AND `_span_type == "end"`

Add `_result != "success"` to filter to errors only.

| Field | Example | Notes |
|---|---|---|
| `_span_name` | `"_http"` | |
| `_span_type` | `"end"` | |
| `_host` | `"api.example.com"` | Hostname only (no scheme or path) |
| `_duration_ms` | `342.0` | Request duration in milliseconds |
| `_result` | `"success"`, `"failure"` | Outcome; use `"success"` for the rate numerator |
| `_status_code` | `"200"`, `"404"`, `"500"` | HTTP status code as string |
| `_request_type` | `"fetch"`, `"script"`, `"image"`, `"xhr"` | How the request was initiated |
| `_path_template` | `"/api/v1/orders/{id}"` | Templated path for grouping (preferred over `_path`) |

---

## SDK initialization

These are emitted regardless of `WebViewConfiguration` flags — they reflect whether the SDK
initialized at all.

### Initialized successfully

**Match:** `_source == "webview"` AND `message == "webview.initialized"`

| Field | Example |
|---|---|
| `message` | `"webview.initialized"` |
| `app_version` | `"1.2.3"` |

### Failed to initialize

**Match:** `_source == "webview"` AND `message == "webview.notInitialized"`

| Field | Example | Notes |
|---|---|---|
| `message` | `"webview.notInitialized"` | |
| `reason` | `"missing_api_key"` | Why initialization failed |
| `app_version` | `"1.2.3"` | |
