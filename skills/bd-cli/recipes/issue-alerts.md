# Issue Alerts

Issue alerts attach to **Issue Views** (saved filtered views of crash/error groups). They fire
based on the volume, frequency, or trend of issues matching the view's filters.

> **Not to be confused with Workflow Alerts** (`bd workflow alert`) which attach to metric chart
> time series. See [workflow-alerts.md](./workflow-alerts.md).

---

## Concepts

An **Issue View** is a saved filter over issue groups — scoped by app ID, platform, time range,
app version, custom event fields, feature flag exposures, or any other issue field. Views are
visible in the Issues UI at `/issues`.

Issue alerts have three components:
1. **New-issue notifications** — fire when a new issue event or issue group appears in the view
2. **Threshold/condition alerts** — fire when issue volume meets a compound condition
3. **Notification channels** — optional routing to Slack, PagerDuty, etc.

---

## CLI Commands

```bash
# List all issue alerts
bd issue alert list --all

# List alerts for a specific view
bd issue alert list --view-id <VIEW_ID>

# List only firing alerts
bd issue alert list --firing

# Get alert config for a view
bd issue alert config <VIEW_ID> -o json

# Create/update alerts on a view
bd issue alert upsert <VIEW_ID> [flags]

# Delete all alerts on a view
bd issue alert upsert <VIEW_ID> --delete

# Alert history
bd issue alert history <VIEW_ID> <ALERT_UUID> --last 7d
```

---

## New-Issue Notifications

These are simple event-driven notifications — no threshold logic. They fire (rate-limited)
whenever the view sees activity.

| Type | Fires when... | API field |
|---|---|---|
| New issue event | Any error in the view occurs | `new_issue_event_notification` |
| New issue group | A previously-unseen error type appears in the view | `new_issue_group_notification` |

Both accept a rate limit (`min_time_between_notifications`). Allowed values: `5m`, `15m`, `1h`.

```bash
# Notify on every new issue event (rate-limited to 1h)
bd issue alert upsert <VIEW_ID> \
  --new-issue-event-notification "group=Mobile Alerts,min_interval=1h"

# Notify on new issue groups (rate-limited to 5m)
bd issue alert upsert <VIEW_ID> \
  --new-issue-group-notification "group=Mobile Alerts,min_interval=5m"
```

---

## Condition-Based Alerts

These fire when issue volume meets a threshold. Created via the `--alert` flag, which uses a
pipe-separated (`|`) key=value format with a `condition=` expression.

### `--alert` flag format

```
--alert "alert_uuid=<UUID>|name=<NAME>|condition=<EXPR>|notification=<SPEC>|per_issue_group=<BOOL>"
```

| Key | Required | Description |
|---|---|---|
| `alert_uuid` | yes | Unique identifier (use a UUID; for new alerts generate one) |
| `name` | yes | Human-readable alert name |
| `condition` | yes | Condition expression (see below) |
| `description` | no | Alert description |
| `notification` | no | Notification spec (`group=<NAME>,min_interval=<DUR>`) — repeatable |
| `per_issue_group` | no | `true` to evaluate per issue group, `false` (default) for across all |
| `disabled` | no | `true` to create in disabled state |
| `label` | no | Key=value label (`KEY=VALUE`) — repeatable |

### Condition expressions

Conditions use a function-call syntax: `name(key=value,key=value)`.

#### Event count threshold

"Errors in this view occur frequently" — fires when event count exceeds threshold in a window.

```
event-threshold(count=100,duration=1h)
```

#### Unique device threshold

Same as event threshold but counts distinct devices.

```
unique-device-threshold(count=50,duration=1h)
```

#### Unique session threshold

Counts distinct sessions.

```
unique-session-threshold(count=50,duration=1h)
```

#### Event-to-app-open percentage

Fires when events as a percentage of total app opens exceeds threshold.

```
event-to-app-open-threshold(percent=0.5,duration=1h)
```

#### Sessions affected percentage

"Errors in this view are trending up" — fires when the percentage of affected sessions
(relative to total sessions for the app_id in the window) exceeds threshold.

**Important:** The percentage is calculated against the gross total sessions for the app_id in
the time window, **ignoring other view filters** (like app version). This means a 1% threshold
means 1% of ALL sessions, not 1% of filtered sessions.

```
event-unique-sessions-to-overall-unique-sessions-threshold(percent=1.0,duration=1h)
```

#### Devices affected percentage

Same concept as sessions but for unique devices.

```
event-unique-devices-to-overall-unique-devices-threshold(percent=1.0,duration=1h)
```

#### Rate of change

Fires when the metric changes by an absolute or percentage amount in a window.

```
event-rate-of-change(window=1h,percentage_change=50,direction=increase)
event-rate-of-change(window=1h,absolute_change=100,direction=increase)
```

#### Compound conditions (AND/OR)

Combine multiple conditions with `and(...)` or `or(...)`. Child conditions are separated by `;`.

```
and(event-threshold(count=100,duration=1h);unique-device-threshold(count=50,duration=1h))
```

---

## Examples

### Alert on high event volume for a release

```bash
bd issue alert upsert <VIEW_ID> \
  --alert "alert_uuid=$(uuidgen)|name=iOS v273 Crash Spike|condition=event-threshold(count=500,duration=1h)|notification=group=Mobile Alerts,min_interval=5m"
```

### Alert when >1% of sessions are affected

```bash
bd issue alert upsert <VIEW_ID> \
  --alert "alert_uuid=$(uuidgen)|name=iOS Session Impact >1%|condition=event-unique-sessions-to-overall-unique-sessions-threshold(percent=1.0,duration=1h)|notification=group=Mobile Alerts,min_interval=15m"
```

### Per-issue-group alert with compound condition

```bash
bd issue alert upsert <VIEW_ID> \
  --alert "alert_uuid=$(uuidgen)|name=High-impact single issue|per_issue_group=true|condition=and(event-threshold(count=100,duration=1h);unique-device-threshold(count=50,duration=1h))|notification=group=Mobile Alerts,min_interval=5m"
```

### Combined: new-issue notifications + threshold alert

```bash
bd issue alert upsert <VIEW_ID> \
  --new-issue-group-notification "group=Mobile Alerts,min_interval=5m" \
  --alert "alert_uuid=$(uuidgen)|name=Crash volume spike|condition=event-threshold(count=1000,duration=1h)|notification=group=Mobile Alerts,min_interval=15m"
```

---

## Workflow: Creating Issue Alerts

1. **Identify or ask the user to create a saved Issue View** in the UI with the desired filters
   (app, platform, version, time range). Views cannot be created via the CLI.
2. **Get the view ID** — ask the user to copy it from the browser URL when viewing the saved
   view (the ID is the path segment after `/issues/views/`). If the view already has alerts,
   you can also find it via:
   ```bash
   bd issue alert list --all -o json --jq '[.items[] | {view_id, view_name}]'
   ```
   Note: this only returns views that already have alerts attached — it cannot discover views
   with no alerts.
3. **Discover notification groups** — list available groups to offer the user a choice:
   ```bash
   bd notification-group list -o json --jq '[.notification_groups[] | .name]'
   ```
4. **Decide on conditions** — prompt the user:
   - Do they want notifications on new issues, volume thresholds, or both?
   - What count/percentage threshold makes sense? (Check current volume in the view)
   - Scope: across all issues or per issue group?
   - Rate limit for notifications? (Allowed: `5m`, `15m`, `1h`)
5. **Create the alert(s)** using `bd issue alert upsert`.

---

## Pitfalls

- **Session/device percentage ignores view filters.** The denominator is ALL sessions/devices
  for the app_id in the window — not filtered sessions. A 1% threshold on a view filtered to
  one version means 1% of all sessions across all versions.
- **`alert_uuid` must be unique.** Use `uuidgen` to generate. If you reuse a UUID, it updates
  the existing alert.
- **Pipe delimiter in `--alert`.** The `|` character separates top-level keys. Nested expressions
  use `,` and `;` — do not use `|` inside conditions.
- **`--new-issue-event-notification` uses the same format as workflow alert notifications:**
  `"group=<NAME>,min_interval=<DURATION>"`.
- **Upserting replaces the entire config.** When updating, pass all alerts and notifications —
  omitted ones will be removed.
- **`per_issue_group=true`** evaluates the condition independently for each issue group in the
  view. Without it, the condition applies to the aggregate across all issue groups.
