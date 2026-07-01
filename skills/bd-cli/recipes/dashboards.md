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

## Chart reference format

When referencing a workflow chart in a `ChartComponentLayout`, use `workflow_id` and
`chart_rule_id`. The `aggregated_action_id` field is optional and every known working dashboard
omits it.

```json
{
  "chart_id": {
    "workflow": {
      "workflow_id": "WORKFLOW_ID",
      "chart_rule_id": "RULE_ID"
    }
  }
}
```

To get `chart_rule_id` values for a workflow:

```bash
bd workflow describe <WORKFLOW_ID> -o json --jq '[.workflow.actions[] | {rule_id, field: .metric_chart_rule.time_series[0].histogram.value.name}]'
```

**Verify against a real dashboard before building.** `bd schema` alone is not sufficient.
Run `bd dashboard get <EXISTING_DASHBOARD_ID> -o json` to see the exact shape a working chart
uses before constructing your own payload.

---

## Section headings and layout

Use `DashboardStylisticComponent` with a `text_component` to add section headings to a tab.
The `variant` field follows HTML heading conventions: `"h1"`, `"h2"`, `"p"`, etc.

**`row_span` must be `3`** for all stylistic components — the API rejects any other value.

```json
{
  "stylistic_components": [
    {
      "id": "heading_latency",
      "text_component": { "text": "Latency", "variant": "h2" },
      "dashboard_layout_settings": {
        "x": 0, "y": 0, "column_span": 12, "row_span": 3, "is_hidden": false
      }
    }
  ]
}
```

Charts use the same grid. A common layout is `column_span: 6, row_span: 3` (two charts per row).
Place chart rows at `y = heading_y + 3` so they appear immediately below their section heading.

---

## Other lifecycle commands

```bash
bd dashboard favorite <DASHBOARD_ID>
bd dashboard delete <DASHBOARD_ID>
```

Use `favorite` for frequently revisited dashboards. Use `delete` only when the dashboard is
obsolete; deleting a dashboard does not delete the underlying workflows.
