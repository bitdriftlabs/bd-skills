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

Each `bd issue alert upsert` call can configure any combination of:
- **New-issue notifications** — fire when a new issue event or issue group appears in the view
- **Condition-based alerts** — fire when issue volume meets a threshold or compound condition

Both types support optional notification channel routing (Slack, PagerDuty, etc.).

---

## New-Issue Notifications

These are simple event-driven notifications — no threshold logic. They fire (rate-limited)
whenever the view sees activity.

| Type | Fires when... |
|---|---|
| New issue event | Any error in the view occurs |
| New issue group | A previously-unseen error type appears in the view |

Both accept a `min_interval` rate limit. Allowed values: `5m`, `15m`, `1h`.

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

Keys are pipe-separated (`|`). `alert_uuid` (use `uuidgen`) and `name` and `condition` are required;
`notification`, `per_issue_group`, `description`, `disabled`, and `label` are optional:

```
--alert "alert_uuid=<UUID>|name=<NAME>|condition=<EXPR>|notification=group=<NAME>,min_interval=<DUR>"
```

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

1. **Get or create the Issue View.** Views can be managed via `bd view` — see
   [recipes/views.md](./views.md) for how to list existing views, find a view ID, or create a new
   one. If the view already has alerts, you can also discover its ID from:
   ```bash
   bd issue alert list --all -o json --jq '[.items[] | {view_id, view_name}]'
   ```
   Note: this only returns views that already have alerts — it cannot discover views with no alerts.
2. **Discover notification groups** — list available groups to offer the user a choice:
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
- **`--new-issue-group-notification` and `--new-issue-event-notification` require a notification
  group.** The CLI rejects these flags if `group=` is omitted — unlike `--alert` conditions, which
  can be created without routing. These flags exist solely to dispatch notifications; without a
  destination they have no effect, so the CLI enforces that a group must exist first.
- **Upserting replaces the entire config.** Never pass only the alerts you want to change —
  omitted alerts and notifications will be deleted. Always re-specify the full set on every upsert.
- **`per_issue_group=true`** evaluates the condition independently for each issue group in the
  view. Without it, the condition applies to the aggregate across all issue groups.
