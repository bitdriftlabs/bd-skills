# Instant Insights

Instant Insights are pre-built workflows **automatically deployed in every bitdrift account** with stable, permanent IDs. They are always running — no setup or deployment needed. Query them directly with `bd workflow charts <ID>`.

**Always check Instant Insights before deploying a custom workflow.** If an existing chart answers the user's question, read that data directly. Only create a new workflow if the user needs filtering or dimensions not covered (e.g. scoped to a specific app version, OS version, or custom field).

> **Future improvement:** There is currently no way to programmatically distinguish Instant Insights from user-created workflows — `bd workflow list` returns both. A `--instant-insights` filter (or similar) would let agents discover IIs dynamically instead of relying on this table. Until that exists, use the IDs below.

## ID Table

| ID | Name | What it measures |
|---|---|---|
| `DKPe` | App Opens | Count of app opens, unique by device |
| `csaK` | Logs by Level | Volume of all logs grouped by severity |
| `nvjF` | App Version Adoption | SDK starts by app version (unique devices) |
| `vX4Q` | Android Paths to Force Quit | Sankey: screens leading to force quit (Android) |
| `PsdH` | iOS Paths to Force Quit | Sankey: screens leading to force quit (iOS) |
| `o30N` | iOS Force Quit Rate | APP_TERMINATION / APP_OPEN rate (iOS) |
| `I1E4` | iOS App Freezes | ANR rate as % of app opens (iOS) |
| `6YYT` | Android App Exit Reasons | Exit reason rates: low memory, force quit, ANR, native crash, exception |
| `VulT` | Android Unhandled Exceptions | Count of APP_CRASH events |
| `MzTH` | App Launch TTI | Histogram of time-to-interaction on launch |
| `YjBZ` | App Install Size | Histogram of `_app_install_size_bytes` on APP_UPDATE |
| `E2qM` | App Disk Usage | Histograms of app directory sizes |
| `W1In` | App Memory Usage | Histograms of JVM, native (Android), and app memory (iOS) |
| `CDj6` | Android Critical Memory Warnings | Count of MEMORY_PRESSURE events |
| `6ZfB` | Android Thermal States | Count of elevated thermal state changes |
| `7Ira` | iOS Critical Memory Warnings | Count of non-normal MEMORY_PRESSURE events |
| `pbNn` | iOS Thermal States | Count of THERMAL_STATE_CHANGE events |
| `CXLl` | Network Success Rate | Overall success rate across all endpoints |
| `gELc` | Success Rate by Endpoint | Success rate grouped by `_path_template` |
| `o4BA` | Requests by Endpoint | Request count grouped by `_path_template` |
| `esfA` | API Latency by Endpoint | Histogram of `_duration_ms` grouped by `_path_template` |
| `z5Aq` | Request Size by Endpoint | Histogram of `_request_body_bytes_sent_count` grouped by `_path_template` |
| `fL3u` | Response Size by Endpoint | Histogram of `_response_body_bytes_received_count` grouped by `_path_template` |
| `f9gv` | Bytes per Minute | Upload/download throughput from RESOURCE events |
| `DC1H` | iOS Network Failures by Type | Count of client errors, 4xx, 5xx (iOS) |
| `7ysf` | Android Network Failures by Type | Count of client errors, 4xx, 5xx (Android) |
| `phsH` | Client-Side Network Failures | Client-side failure counts (both platforms) |
