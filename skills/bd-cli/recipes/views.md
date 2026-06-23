# Views

A **view** is a saved filter over either issue groups or workflows. Use views to preserve a working
set, share it, or reapply the same filters later from CLI commands. Issue alerts still require an
**issue-group** view ID: every `bd issue alert` operation targets a view by ID.

---

## Filter modes

Views have three filter modes, selected at creation time via `--filter-mode`:

| Mode | When to use |
|---|---|
| `issue-group-query` | Modern mode — filter by platform, app, status, assignee, time range, feature flags, advanced conditions. Use for all new views. |
| `issue-group-list` | Legacy mode — pins specific issue group IDs. Only use if required by an existing workflow. |
| `workflow-list` | Saved workflow query — filter by workflow state, workflow IDs, names, favorites, tags, and access predicates. Use when the goal is to revisit or reuse a workflow slice. |

---

## Getting a view ID

When the view already exists, list and filter by name:

```bash
bd view list --all -o jsonl --jq '{id, name}'
```

Or fuzzy-search:

```bash
bd view list --name "iOS Crashes" -o jsonl --jq '{id, name}'
```

To narrow by service type first:

```bash
bd view list --service-type issue-group --all -o jsonl --jq '{id, name}'
bd view list --service-type workflows --all -o jsonl --jq '{id, name}'
```

---

## Creating an issue-group view

```bash
bd view create \
  --name "iOS v273 Crashes" \
  --filter-mode issue-group-query \
  --platform apple \
  --app-id com.example.ios \
  --status new --status reopened \
  --last 7d \
  -o json --jq '.view.id' -r
```

For available filter flags run `bd view create --help`. Non-obvious: `--advanced-condition` takes
`lhs=<FIELD>,op=<OP>,rhs=<VALUE>,group=<N>` — conditions sharing the same `group` number are OR'd
together; different group numbers are AND'd.

---

## Creating a workflow view

```bash
bd view create \
  --name "Live Payments Workflows" \
  --filter-mode workflow-list \
  --workflow-state live \
  --tag-condition operator=includes,match=all-of,tags=payments|critical,group=1 \
  --default-sort key=display-name,direction=asc \
  -o json --jq '.view.id' -r
```

Workflow views are the right tool when the same workflow slice needs to be revisited or applied to
`bd workflow list --view-id <id>`. Useful filters include:

- `--workflow-state`
- `--workflow-id`
- `--workflow-name`
- `--favorited` or `--not-favorited`
- `--tag-condition`
- `--access-condition`

For `--tag-condition`, conditions in the same `group` are ANDed together, and different groups
become OR branches.

---

## Reusing a view ID

View IDs are not just for `bd view` commands; they can also drive filtered list commands:

```bash
bd issue group list --view-id <VIEW_ID>
bd workflow list --view-id <VIEW_ID>
```

Use an issue-group view ID with `bd issue group list`. Use a workflow view ID with
`bd workflow list`.

---

## Create a view and attach issue alerts in one step

```bash
VIEW_ID=$(bd view create \
  --name "iOS v273 Crashes" \
  --filter-mode issue-group-query \
  --platform apple \
  --app-id com.example.ios \
  --status new --status reopened \
  --last 7d \
  -o json --jq '.view.id' -r)

bd issue alert upsert "$VIEW_ID" \
  --alert "alert_uuid=$(uuidgen)|name=Crash spike|condition=event-threshold(count=500,duration=1h)|notification=group=Mobile Alerts,min_interval=5m"
```

---

## Updating a view

`update` patches metadata (name, description, icon) without touching filters unless
`--replace-filters` is supplied. When you do supply it, all current filters are replaced — re-specify
every filter you want to keep.

```bash
# Rename only
bd view update <VIEW_ID> --name "iOS v274 Crashes"

# Replace filters entirely
bd view update <VIEW_ID> \
  --replace-filters issue-group-query \
  --platform apple \
  --app-id com.example.ios \
  --status new --status reopened --status in-progress

# Replace a workflow view's filters entirely
bd view update <VIEW_ID> \
  --replace-filters workflow-list \
  --workflow-state live \
  --workflow-name "payments" \
  --tag-condition operator=includes,match=any-of,tags=payments|checkout,group=1
```

---

## Pitfalls

- **`--replace-filters` is an all-or-nothing replacement.** Any filter not re-specified in the
  update is cleared. Always re-apply every filter you want to keep.
- **Filter mode cannot be changed on an existing view.** To switch from `issue-group-list` to
  `issue-group-query` or `workflow-list`, delete and recreate the view.
- **`bd view list` is paginated.** Always pass `--all` to fetch the full list, or `--name` to
  fuzzy-filter before paginating.
