# Workflow Lifecycle

This recipe covers creating, deploying, updating, and managing workflows. For the proto schema and match rule reference, see [workflow-schema.md](../reference/workflow-schema.md).

---

## Choose the right mode first

Before deploying anything, decide which kind of help the user needs:

### Active investigation

Use this path when the user is debugging an issue that is happening now or very recently and wants
to understand real user impact, inspect a concrete session, or confirm a suspected regression.

- Prefer **existing evidence** first: Instant Insights, issue groups, existing captured sessions,
  and already-deployed workflows.
- When looking for an applicable existing workflow, use the workflow description in metadata to
  identify what the workflow is intended to detect, measure, or capture and why it was created.
- Only deploy a new `flush_rule` workflow if existing data cannot answer the question.
- Before deploying live capture, confirm the target behavior is still occurring in the current
  window. Live capture only observes **new** sessions after deployment.

### Ongoing data collection

Use this path when the user wants durable measurement over time: funnels, adoption, long-running
comparisons, cohort analysis, or persistent monitoring.

- Treat the task as workflow design, not incident response.
- Optimize for signal quality, grouping, aggregation, and the right time horizon.
- Session capture may still be useful, but it is not the default.

If timing is unclear, determine that first. Do not assume a 24h aggregate means the issue is still
active right now.

---

## Choose workflow granularity deliberately

Use **one workflow for one analytic question or one coherent flow**. If the user is really asking
about several related but distinct signals, prefer multiple workflows rather than one large
catch-all workflow.

Split into multiple workflows when:

- the entry points represent different user journeys
- different teams would reason about the results independently
- the outputs are better compared side by side than merged into one workflow definition
- the workflow has grown into a presentation artifact instead of a measurement artifact

When the goal is a multi-panel operational view, build multiple focused workflows and compose their
charts into a dashboard. Do not use workflow complexity as a substitute for dashboard composition.

Large multi-entry workflows are still valid when the entries truly form one shared funnel or one
tightly related measurement problem, but examples like a 14-entry-point operational board should be
treated as a smell and revisited first.

---

## Creating a Workflow

Use `bd workflow create --help` for the command shape and `bd schema workflow.create` for the file
inputs and JSON types.

The workflow payload itself lives in `Workflow`. The optional companion files serve different
purposes:

- `--metadata-file` sets workflow metadata such as description and per-rule panel titles
- `--chart-metadata-file` sets per-series chart metadata such as legend labels

When creating a workflow, set the workflow description in metadata (typically via
`--metadata-file`). Use it to explain the workflow's purpose: what it is trying to measure,
detect, or capture, and, critically, why this workflow is being created at all (for example,
to investigate a suspected regression, monitor adoption, or validate a hypothesis). Focus on capturing
the intent over describing what the workflow does as this can be inferred from the configuration.

## Organizing workflows with tags

Use workflow tags to organize related workflows after the workflow boundaries are already sound.
Tags help with discovery and saved workflow views, but they do **not** fix a workflow that should
really be split apart.

```bash
bd workflow tag list
bd workflow tag set <WORKFLOW_ID> --tag payments --tag critical
```

`bd workflow tag set` replaces the entire tag set for the workflow. Re-specify every tag you want
to keep.

## Updating a Workflow

Use `bd workflow update --help` for the accepted flags and `bd schema workflow.update` for the file
inputs.

The durable workflow-level rule is: **stop deployed workflows before editing workflow logic.**
Metadata and chart metadata can be updated independently of the workflow graph.

When updating a workflow, also update the description in metadata if the workflow's purpose, scope,
or reason for existing has changed. Keep the description aligned with both what the workflow does
and, if relevant, why the team is running it.

## Using `describe` as a Template

`bd workflow describe <id> -o json` returns the full workflow proto. To use it as a create/update
template, **strip server-managed fields first.** Check `bd schema workflow.create Workflow --docs`
and remove any field documented as server-generated or immutable, even if an older example still
shows it.

## Deploy-and-Wait Pattern

Use this pattern for **active investigations** when the user needs fresh sessions from a condition
that is still happening now.

1. **Confirm current activity** — before deploying, verify the target phenomenon is still present
   in the recent window. For example: recent requests for an endpoint, fresh crashes, or a current
   latency spike.
2. **Deploy** — create with a `flush_rule` triggered by the condition.
3. **Set a temporary lifetime** — use `deployment_expiration` for investigative workflows unless
   the user explicitly wants a durable workflow.
4. **Poll** — check `bd workflow captured-sessions <id> -o json --last 24h` periodically. An empty
   result means no matching sessions yet — not necessarily an error.
5. **Branch on no hits** — distinguish between no current traffic, no current failures, propagation
   delay, and an overly narrow match before broadening the workflow.
6. **Iterate** — if needed, lower the threshold, broaden the match, or verify that the SDK is
   active on the target devices.

Do **not** use this pattern to recover historical sessions that happened before the workflow was
deployed. If the user needs past evidence, prefer issues, existing sessions, or already-captured
workflow data.

---

## VIP / Known Entity Capture

Use this pattern when the user wants **guaranteed session capture for specific users** — customer support escalations, executives, internal testers, or high-value accounts.

### Prerequisites

1. The app calls `setEntityID` / `setEntityId` with the user's identifier (iOS/Android SDK 0.23.0+)
2. The entity has been bookmarked in the bitdrift UI, or created via `bd entity known upsert <entity_id> --display-name "Name"`

### Why this beats the old field-match workaround

The previous approach was to deploy a `generic_match` workflow filtering on a `user_id` field. That workflow deployed to **every device in the fleet** and matched on each one — wasteful and noisy. `known_entity_match` is evaluated against the server-managed known-entity set, so it only fires for bookmarked entities.

### Workflow JSON

```json
{
  "flows": [
    {
      "exclusive": {},
      "steps": [
        {
          "match_rule": {
            "match_id": "vip-session",
            "known_entity_match": {}
          }
        }
      ],
      "action_rules": [
        {
          "rule_id": "capture-vip",
          "flush_rule": {
            "match_id": "vip-session"
          }
        }
      ]
    }
  ]
}
```

Deploy with `bd workflow create --workflow-file <file>` then `bd workflow deploy <id>`. No `deployment_expiration` — this should be a durable workflow that covers all current and future bookmarked entities automatically.
