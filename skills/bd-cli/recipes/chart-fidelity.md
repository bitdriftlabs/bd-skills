# Grouped Chart Fidelity and Recovery

Use this file only after you have already observed a grouped-chart fidelity warning or another
grouped-chart edge case. For normal chart reads, stay in `charts.md`.

## `IdentifierMatch`: reuse returned series, don't invent selectors

When the schema/docs say to use `IdentifierMatch`, build each `dimension_identifiers[]` entry from a
previous grouped chart response:

- `id` = `time_series[].id`
- `labels` = the full `time_series[].labels[]` set for that grouped result

The `id` is **not** unique by itself for grouped charts. Multiple returned groups can share the
same `time_series.id`, so always send the matching labels with it.

```bash
# Discover candidate groups first
bd workflow charts <workflow> -o json --last 24h \
  --jq '[.data[0].line_data.time_series[] | {id, labels, rollup: .aggregated_rollup}]'
```

Then construct `bd charts load --request-file ...` using the returned `id + labels` pairs.

Do not:

- invent placeholder IDs
- assume labels alone are enough unless the live schema explicitly says so
- assume a single `time_series.id` maps to only one group

## Distinguish the three fidelity warnings

These fields mean different things and lead to different next steps:

| Signal | What it means | Can query changes help? | How to answer |
|---|---|---|---|
| `query_group_by_collapsed = true` | This query asked for too many distinct groups, so the backend collapsed the result at query time | **Yes, sometimes** | Do not rank groups yet; reduce query cardinality first |
| `group_by_overflows > 0` | Per-group detail was already dropped upstream (`Client` and/or `ServerGroupBy`) | **Not for affected intervals** | Say the grouped breakdown is incomplete |
| `total_overflows > 0` | Total-cardinality drops already happened upstream (`ServerTotal`) | **Not for affected intervals** | Say even totals may be incomplete |

## Recovery sequence

### Case 1: `query_group_by_collapsed = true`

Treat this as a **query-shape** problem first.

Try, in this order:

1. Shorten the time window
2. Add tighter filters
3. Narrow app version / rollout scope
4. Switch to a lower-cardinality grouping field
5. If the user still needs a long-range answer, query several smaller windows and aggregate the
   results externally, clearly saying you reconstructed the result from smaller windows

Do **not** treat `--top-k` as the first fix here. Collapse happens because the query produced too
many active groups, not because the returned head/tail view was too small.

### Case 2: `group_by_overflows > 0`

Treat this as **upstream loss of grouped detail**.

- You may still use overall totals more cautiously than rankings
- You should not claim the returned ranking is complete for affected intervals
- Narrowing the time window can help isolate periods without drops, but it does not recover missing
  groups inside affected periods

### Case 3: `total_overflows > 0`

Treat this as the strongest warning.

- Some data was dropped before query time
- Even totals may be incomplete for affected intervals
- Narrowing the query can help isolate unaffected periods, but it cannot reconstruct dropped data

## How to talk about it

Use wording like this in responses:

### Query-time collapse

> This chart collapsed at query time (`query_group_by_collapsed=true`). That means this specific
> query asked for too many distinct groups; it does not necessarily mean the underlying data was
> dropped. I should narrow the time range or add tighter filters before ranking groups.

### Upstream group-by loss

> This chart has upstream group-by overflow (`group_by_overflows > 0`). The overall metric may still
> be useful, but the returned breakdown is incomplete for the affected intervals.

### Upstream total-cardinality loss

> This chart has upstream total-cardinality overflow (`total_overflows > 0`). Some data was dropped
> before query time, so even totals may be incomplete for the affected intervals.

## `--top-k` when fidelity warnings are present

If `query_group_by_collapsed = true`, changing `--top-k` is usually not the right first move.
Reduce query cardinality first.

## When to stop and recommend workflow changes

If the chart repeatedly shows upstream overflow (`group_by_overflows` or `total_overflows`) and the
question depends on complete rankings or long-tail analysis, say that the current workflow is not
collecting the needed fidelity and suggest a lower-cardinality grouping field (for example
`_path_template` instead of `_path`) or a different workflow design.
