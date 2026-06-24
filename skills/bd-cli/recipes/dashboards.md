# Dashboards

A **dashboard** is the composition layer for chart outputs. Use dashboards to present related
signals from multiple workflows in one place. Do not use a dashboard as a substitute for workflow
logic, and do not stretch one workflow into many unrelated entry points just to get a single screen.

---

## Start with schema discovery

Dashboard create and update use protobuf JSON payloads. Before writing a request file, inspect the
live contract:

```bash
bd schema dashboard
bd schema dashboard.create
bd schema dashboard.create UpsertCustomDashboardRequest --depth 2
bd schema dashboard.create Chart --depth 2
```

Use the live schema as the source of truth for request and response fields. Query nested dashboard
types directly when you need exact payload details instead of relying on a hand-maintained schema
reference file.

---

## Listing and opening dashboards

```bash
bd dashboard list --all -o jsonl --jq '{id, name, owner_name}'
bd dashboard list --query "checkout" -o jsonl --jq '{id, name}'
bd dashboard get <DASHBOARD_ID> -o json
bd dashboard open <DASHBOARD_ID> -o json --jq '.url' -r
```

Use `--favorites-only` or `--sort-by` when narrowing to an existing dashboard is faster than
building a new one.

---

## Creating and updating dashboards

Create and update both take a request file for `UpsertCustomDashboardRequest`:

```bash
bd dashboard create --request-file dashboard.json --open
bd dashboard update <DASHBOARD_ID> --request-file dashboard.json --open
```

Practical workflow:

1. Identify the workflows whose charts belong together.
2. Confirm each workflow has one clear purpose and is not serving as a catch-all.
3. Use `bd dashboard create` or `update` to compose those existing chart outputs into one view.
4. Prefer revising workflow boundaries before adding more unrelated entry points to an already large
   workflow.

If you need the dashboard only as a curated landing page for existing metrics, keep the workflows
separate and let the dashboard do the composition work. For the higher-level workflow-vs-dashboard
decision rule, follow the guidance in the main `bd-cli` skill before loading this recipe.

---

## Other lifecycle commands

```bash
bd dashboard favorite <DASHBOARD_ID>
bd dashboard delete <DASHBOARD_ID>
```

Use `favorite` for frequently revisited dashboards. Use `delete` only when the dashboard is
obsolete; deleting a dashboard does not delete the underlying workflows.
