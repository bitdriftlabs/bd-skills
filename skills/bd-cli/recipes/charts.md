# Reading Chart Data

Use `bd workflow charts <workflow_id>` to read metric data from any deployed workflow, including all 27 Instant Insights.

Chart configuration lives in the workflow proto's `actions[]` — there is no separate config layer.

Stopped workflows return no new data but historical data is still accessible.

If you actually hit grouped-chart sharp edges — `IdentifierMatch`, `query_group_by_collapsed`,
non-zero `group_by_overflows` / `total_overflows`, or ambiguity about whether changing the time
window can help — then read [chart-fidelity.md](./chart-fidelity.md) before drawing conclusions.
Do not load it preemptively for clean grouped-chart reads.

**Error handling:** Response `data[]` entries can contain an `error` string instead of chart data. Always check for `.error` before accessing `.line_data`:
```bash
bd workflow charts <id> -o json --last 24h \
  --jq '[.data[] | select(.error) | {chart_id: .chart_id.workflow.chart_rule_id, error}]'
```

## Grouped chart fidelity

Before interpreting any **grouped** chart (by endpoint, app version, screen, error type, or any
other dimension), run this check first:

1. Check for `.error` entries in `data[]`.
2. Check `.line_data.time_series[].cardinality_overflows` and whether `query_group_by_collapsed` is true.
3. Check whether the result is only a top-K subset plus `other`.
4. Only then rank groups or compare multiple charts.

A top-K subset without cardinality warnings is a normal truncation — the visible head is reliable,
but the tail is omitted. Cardinality warnings are a different class of problem: grouped charts can
silently lose fidelity when the `group_by` field is too high-cardinality (for example raw user IDs,
request IDs, or `_path` instead of `_path_template`). Use `bd schema workflow.charts --docs` to
inspect the `cardinality_overflows` field shape and docs.

Once you detect a warning, decide whether you are looking at query-time collapse, upstream loss,
`IdentifierMatch` targeting, or a combination. Reach for raw request JSON only when you need
per-chart `limit_strategy`, identifier targeting, or different histogram settings. Consider session
logs only after the chart/query options are exhausted.

```bash
# Surface grouped series with cardinality warnings
bd workflow charts <id> -o json --last 24h \
  --jq '[.data[].line_data.time_series[]? |
    select(.cardinality_overflows != null and (
      .cardinality_overflows.total_overflows > 0 or
      .cardinality_overflows.group_by_overflows > 0 or
      .cardinality_overflows.query_group_by_collapsed
    )) |
    {
      title: (.legend.title // .title),
      labels: .labels,
      cardinality_overflows: .cardinality_overflows
    }]'
```

If the workflow was just created or is still editable, consider changing the workflow rules to
collect lower-cardinality data instead (for example use a normalized field such as
`_path_template` rather than `_path`).

---

## JSON Output Shape

Use `bd schema workflow.charts` to explore the full response shape. Key fields for jq:

| Path | What it is |
|---|---|
| `data[]` | One entry per chart action (`metric_chart_rule` / `sankey_diagram_rule` / `funnel_rule`) |
| `.chart_rule_id` | Matches the `rule_id` in the workflow proto |
| `.line_data.time_series[]` | One series per grouped dimension; ungrouped = one series |
| `.time_series[].data[].value` | Numeric, or `"NaN"` for empty buckets |
| `.time_series[].aggregated_rollup` | Summary value for the whole query window (see chart-type notes below) |
| `.time_series[].cardinality_overflows` | Overflow metadata for grouped series; check this before trusting the breakdown |
| `.time_series[].labels[]` | Group-by dimension values |
| `.time_series[].labels[] | select(.name == "percentile")` | Histogram percentile returned for that series when applicable |
| `.aggregation_window` | Bucket size (e.g. `"900.000000000s"` = 15 min) |

## Answering strategy

When the user asks for "what's worst", "top offenders", or "which endpoint is biggest", prefer a
progressive-disclosure answer over jumping straight to the most exhaustive reconstruction.

- **Clean grouped chart, enough visible head** — answer directly.
- **Top-K only, no cardinality warnings** — answer as the **visible top offenders**, mention that
  the tail is omitted, and only go deeper if the user wants more rigor.
- **Any fidelity warning** — switch to [chart-fidelity.md](./chart-fidelity.md). That file is the
  source of truth for whether you can still give a directional answer, need to narrow the query
  first, or should avoid ranking altogether.
- **Proxy metrics** — if you combine histogram size charts with request counts, or otherwise infer a
  ranking indirectly instead of querying the exact total, present the result as an approximation
  rather than as the final truth.

For simple one-number lookups, prefer a direct path over investigation mode. If you already know
the workflow ID or chart to query — from the skill reference, a prior step, or a preflight check —
query that chart first and stop once you have a trustworthy user-facing answer. Do not broaden into
workflow search, schema exploration, or scalar-path inspection unless the direct query fails or the
result is ambiguous.

## Top-K and Secondary Metrics

Some grouped charts return only a top-K subset of groups plus an `other` bucket. This means the
returned series are only the visible head of the distribution, not the full population.

Top-K selection is based on a smoothed view of the queried time range, not a simple whole-window
sum or percentile rank. Use `--sort-by` and `--top-k` to change which groups are returned, but do
not assume two different top-K charts describe the same set of groups.

Top-K truncation also happens **before** any post-query cleanup you do yourself. If you later
normalize or merge returned groups into broader families — for example collapsing
`/product/123`, `/product/456`, and `/product/789` into `/product/{id}` after the query returns —
those family totals can still be biased downward because some concrete members may never have made
it into the returned top-K set.

Do **not** rank one metric using another metric's top-K output. For example, a top-K response size
chart can show which returned groups have large responses, but it does not reliably identify the
same endpoints that would appear in a top-K request size chart.

If the returned top-K head is not enough to answer the question:

- If there are **no** cardinality warnings, this is a normal top-K limitation: try `--top-k` and
  `--sort-order` on the chart query.
- If there **are** cardinality warnings (`query_group_by_collapsed`, `group_by_overflows`, or
  `total_overflows`), follow the warning-specific guidance in the answering strategy above.

When completeness matters, do a saturation check before claiming you have the full ranking:

1. Increase `--top-k` on the densest representative slice.
2. See whether the head of the ranking and the aggregated family totals stabilize.
3. If the totals move materially as `--top-k` increases, say the answer is still lossy /
   directional rather than complete.
4. Prefer querying a field that is already normalized to the desired grouping level over relying on
   post-hoc merging of many concrete values.

## Aggregation Window Scaling

The bucket size depends on the queried time range:

| Time range | Aggregation window |
|---|---|
| < 4 hours | 1 minute |
| 4–36 hours | 15 minutes |
| > 36 hours | 2 hours |

This affects Min/Max calculations and trend detection granularity. A 7-day query uses 2-hour buckets — short spikes may be smoothed out.

---

## Interpreting Output by Chart Type

### Count
One series per group-by dimension. `value` is the count in each bucket.
`aggregated_rollup` is the total count across the whole query window for that series. For grouped
count charts, summing `aggregated_rollup` across series gives the grand total volume.

### Rate
One series per group-by dimension. `value` is the rate in each bucket. `aggregated_rollup` is the
rolled-up rate for the entire query window, computed from the raw numerator and denominator counts
across buckets.

Do **not** treat `aggregated_rollup` on a rate chart as request volume, failure volume, or the sum
of bucket values. Do **not** sum `aggregated_rollup` across series. If you need counts behind the
rate, sum `.data[].rate_details.numerator_count` and `.data[].rate_details.denominator_count`.

### Histogram
`value` is a percentile. `aggregated_rollup` is the same
statistic computed over the entire query window (for example, a whole-window p95), not a total
volume. Use this to report the percentile value over the whole time period.

Use `data[]` or the histogram bar chart response when you need the distribution itself.

Prefer pinning the percentile when a histogram result will be compared, reported, or used in
follow-up reasoning. This makes the query deterministic and keeps comparisons across charts or time
ranges honest.

Always name the percentile when reporting a histogram result. If the caller pinned the percentile
explicitly (for example with `--percentile` or `HistogramConfiguration.percentile`), report that
configured percentile. Otherwise, read the percentile back from the response labels rather than
guessing:

```bash
bd workflow charts <id> -o json --last 24h \
  --jq '[.data[0].line_data.time_series[] | {
    percentile: (.labels[]? | select(.name == "percentile") | .value),
    value: .aggregated_rollup
  }]'
```

Do not say "latency is 120 ms" or "response size is 30 KB" without also stating which percentile
that represents.

### Table
Returned when a count or rate chart has `group_by` and `table_display_mode` set. Data is in
`.table_data.tables[]` with `rows[]` containing `group_column_values` and `aggregated_values`.
`aggregated_values` follow the semantics of the backing chart: count totals for count charts,
rolled-up rates for rate charts.

### Histogram Bar Chart
Returned for histogram charts. Data is in `.histogram_bar_chart_response`, where the bar values
represent counts per histogram bucket rather than a single rolled-up total.

### Sankey
Data is in `.sankey_data` with `nodes[]` (each has `id` and `name`) and `links[]` (each has
`source_node_id`, `target_node_id`, `value`). `value` is the path count for that edge.

```bash
# Find which screen has the most paths to a terminal node
bd workflow charts <id> -o json \
  --jq '[.data[0].sankey_data.links[] | select(.target_node_id | startswith("App Will Terminate")) | {screen: .source_node_id, count: (.value | tonumber)}] | sort_by(-.count)'
```

### Funnel
Data is in `.funnel_data.steps[]` — each step has `id` (matches `match_id`) and `value` (session
count reaching that step). Compare consecutive `value` fields to find drop-off points.

---

## Interpreting Chart Data

### Identifying worst performers from grouped series

For grouped **rate** charts, sort by `aggregated_rollup` when you want the lowest or highest rate:

```bash
# Worst series by rate (lowest first)
bd workflow charts <id> -o json --last 24h \
  --jq '[.data[0].line_data.time_series[] | {name: ((.labels[]? | select(.name == "_path_template") | .value) // .legend.title // .title), rate: .aggregated_rollup}] | sort_by(.rate)[:10]'
```

To get the **raw counts** behind a rate, sum `rate_details` across buckets — `aggregated_rollup` is the rolled-up rate, not a count:

```bash
bd workflow charts <id> -o json --last 24h \
  --jq '[.data[0].line_data.time_series[] |
    {
      name: ((.labels[]? | select(.name == "_path_template") | .value) // .legend.title // .title),
      numerator: ([.data[] | select(.rate_details != null) | (.rate_details.numerator_count | tonumber)] | add // 0),
      denominator: ([.data[] | select(.rate_details != null) | (.rate_details.denominator_count | tonumber)] | add // 0)
    }]'
```
