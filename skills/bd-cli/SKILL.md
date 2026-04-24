---
name: bd-cli
description: "Guide for using the bitdrift bd CLI — investigating app health, authoring workflows, reading charts/sessions/issues. Trigger when the user mentions bd, bitdrift, app health investigation, workflow creation, or any bitdrift CLI operation. Use for help debugging apps."
---

# bd CLI

This skill teaches you how to work with the `bd` command-line tool and the bitdrift platform. It covers both the CLI mechanics (output modes, filtering, discovery) and domain-specific knowledge for investigating apps, authoring workflows, and reading platform data.

## Setup

The developer needs:

1. The `bd` CLI: `brew tap bitdriftlabs/bd && brew install bd` if not installed - offer to call this for the user.
2. Authentication: See Authentication section below.

Direct the user to sign up at https://bitdrift.io/signup if new.

## Discovering commands

The CLI is self-documenting. Use `--help` at any level:

```bash
bd --help                    # top-level commands
bd workflow --help           # subcommands within workflow
bd workflow list --help      # flags for a specific command
```

### Schema-first discovery

`bd schema` is the primary way to learn what a command supports: request and response shapes,
field names, enum values, and current proto docs. **Always check `bd schema` before constructing
`--request-file` payloads or writing `--jq` filters on unfamiliar output.** Do not infer field
names, nesting, or accepted values from examples in this skill alone. If examples, older docs, or
UI text use different wording, trust `bd schema`. Sub-files in this skill provide interpretation,
patterns, and pitfalls — not the live contract.

```bash
bd schema                                     # list all command groups
bd schema workflow                            # list commands in a group
bd schema workflow.create                     # request + response schemas (depth=1)
bd schema workflow.create Workflow --depth 3  # drill into a nested type
bd schema workflow.create --docs              # include proto field documentation
```

**Depth controls detail:** `--depth 0` for a quick field inventory, higher depth to expand nested types. Add `--docs` to include proto field documentation. Add `-ojson` for machine-readable output.

For OOTB enums, you can drill into a specific value to inspect its well-known fields:

```bash
bd schema workflow.create GenericOotbConditionType.APP_LAUNCH
```

This shows the field key, type, description, platform, and unit for that event.

**Workflow:**
1. **Building a `--request-file` payload** — run `bd schema <group>.<command>` to see the request
   shape, then `bd schema <group>.<command> <TypeName> --depth 2` to expand the types you need.
2. **Inspecting unfamiliar output** — run `bd schema <group>.<command>` to see the response shape,
   then do a small live probe (`--jq 'keys'`), then write `--jq` filters against the live field names.
3. **Understanding a specific type** — run `bd schema <group>.<command> <TypeName> --depth 3` to
   see nested fields, current names, and enum docs.
4. **Understanding a specific enum value** — run `bd schema <group>.<command> EnumType.VALUE` to
   inspect the fields and metadata attached to that value.

For product-level context — conceptual guides, feature overviews, SDK setup — use the `$bd-docs` skill, which searches docs.bitdrift.io directly. For API-level field names and types, prefer `bd schema`.

## Domain routing

This skill includes reference files, recipes, and runbooks for domain-specific tasks. Read these on demand — don't load them all upfront.

| Intent | File | What's in it |
|---|---|---|
| Look up Instant Insights IDs | [reference/instant-insights.md](reference/instant-insights.md) | 27 permanent workflow IDs for pre-built metrics |
| Create, edit, or understand a workflow | [reference/workflow-schema.md](reference/workflow-schema.md) | Workflow patterns, match rules, actions, OOTB match gotchas, pitfalls; use `bd schema` for the live supported shape |
| Read chart / metric data | [recipes/charts.md](recipes/charts.md) | Interpretation by chart type, aggregation scaling, NaN handling, grouped-chart fidelity checks |
| Fetch and analyze session timelines | [recipes/sessions.md](recipes/sessions.md) | When to use `timeline search` vs `timeline logs`, hydration, search patterns, pitfalls |
| Browse crash reports and issue groups | [recipes/issues.md](recipes/issues.md) | Advanced filters, status lifecycle, triage patterns |
| Create or edit workflow recipes | [recipes/workflows.md](recipes/workflows.md) | Lifecycle commands, metadata files, template workflow patterns |
| Manage API keys, SDK keys, connectors | [recipes/admin.md](recipes/admin.md) | Key creation, permissions, connector setup |

## Output modes

Every command supports `-o` / `--output` to control formatting:

| Mode | Flag | Behavior |
|---|---|---|
| Human | `-o human` (default) | Pretty-printed terminal output. Good for quick looks, bad for parsing. |
| JSON | `-o json` | Full JSON response. |
| JSONL | `-o jsonl` | Newline-delimited JSON — one object per line. Falls back to `json` if unsupported. |

`bd` writes progress and status messages to stderr. Use `2>/dev/null` when piping to jq or saving to a file.

The flag can go before or after the subcommand — both work:
```bash
bd -o json workflow list
bd workflow list -o json
```

### When to use which

- **Interactive exploration**: skip `-o` entirely
- **Extracting specific fields**: `-o json` with `--jq`
- **Streaming or line-by-line processing**: `-o jsonl`

## Pagination

Commands that return lists support `--offset` and `--limit`:

```bash
bd workflow list --limit 25 --offset 50
```

Not all commands paginate — some (like `bd workflow charts`) return all data in one response.

## --jq: built-in filtering

The CLI has a built-in `--jq` flag that applies a [jq](https://jqlang.github.io/jq/manual/) filter to output — no external `jq` binary needed.

```bash
bd workflow list -o json --jq '[.workflows[] | {id, name: .name, status}]'
```

`--jq` requires `-o json` or `-o jsonl`. With `json`, the filter runs once on the full response. With `jsonl`, the filter runs per line.

### -r / --raw-output

Use `-r` to print bare strings instead of JSON-quoted strings — identical to `jq --raw-output`:

```bash
bd workflow describe abc123 -o json --jq '.workflow.name' -r
```

`-r` only affects strings. Numbers, booleans, objects, and arrays render as JSON regardless.

### Common patterns

These examples show **jq patterns**, not guaranteed response schemas. Before reusing one on an
unfamiliar command or output shape, run `bd schema <group>.<command>` first and then confirm with a
minimal live probe. If the examples here use older field names or wording, update them to match the
live schema.

```bash
# List with projection
bd workflow list -o json --jq '[.workflows[] | {id, name: .name, status}]'

# Count results
bd issue group list -o json --jq '.issue_groups | length'

# Filter then project
bd workflow list -o json --jq '[.workflows[] | select(.status == "DEPLOYED") | {id, name: .name}]'

# Extract a single scalar
bd workflow charts CXLl -o json --jq '.data[0].line_data.time_series[0].aggregated_rollup'

# Flatten nested structures
bd issue group list -o json --last 7d --jq '[.issue_groups[] | {reason: .metadata.reason, users: .stats.user_count}]'
```

## Linking to the web UI

Use `open` with `-ojson --jq .url -r` to get a web UI URL without opening a browser:

```bash
bd workflow open <id> -ojson --jq .url -r
bd issue group open <id> -ojson --jq .url -r
bd issue open <id> -ojson --jq .url -r
bd timeline open <id> -ojson --jq .url -r
```

**Always include a link when referencing a resource in your response** — it lets the user click through to the full web UI view.

## Time ranges

Use `--last` to query for a period leading up until now, e.g. `--last 7d`. Use `--since`/`--until` for precise period comparisons using RFC3339 strings.

**Always make sure you understand what time range we are investigating**. If it is not clear from the context what time period we want to prompt the user
for more information. `--last 24h` is a reasonable starting point for when the user is asking about current events, but we may narrow or widen this as more
information appears.

**Prior-period comparison:** Use `--since`/`--until` to compare the current window against the previous one:

```bash
# Current 24h
bd workflow charts <id> -o json --last 24h --jq '<extract value>'

# Previous 24h
bd workflow charts <id> -o json \
  --since "$(date -u -v-48H +%Y-%m-%dT%H:%M:%SZ)" \
  --until "$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ)" \
  --jq '<extract value>'
```

## Investigation mode

Decide: **active investigation** (something happening now — start with existing charts, issues,
sessions) or **ongoing data collection** (measure over time — treat as workflow design). See
[recipes/workflows.md](recipes/workflows.md) for the full decision framework.

- **Active** → [recipes/charts.md](recipes/charts.md), [recipes/issues.md](recipes/issues.md),
  [recipes/sessions.md](recipes/sessions.md), [recipes/workflows.md](recipes/workflows.md)
- **Ongoing** → [recipes/workflows.md](recipes/workflows.md),
  [reference/workflow-schema.md](reference/workflow-schema.md), [recipes/charts.md](recipes/charts.md)

A new capture workflow only sees **new** sessions after deployment — it cannot recover historical data.

### Population-level questions

When the question is about ranking, comparing, or aggregating across many users or devices — not
inspecting a single session — start with grouped charts, not session timelines. Default to the
**lightest trustworthy answer first**: prefer the shortest honest answer the existing grouped chart
can support. Before answering from a grouped chart, load
[recipes/charts.md](recipes/charts.md) for the answering strategy and fidelity checks.

### Simple metric lookups

Some requests are direct metric lookups rather than broad investigations. When the relevant
workflow or chart is already known from this skill, prior discovery, or other explicit context,
query that workflow/chart directly before broad workflow discovery.

## Scoping to an app

**Always scope to an app during investigations.** Unscoped queries return data from every app in the account, wasting context and producing misleading results.

Commands that query app-specific data (charts, issues, sessions) accept:

```bash
--app-id <BUNDLE_ID> --platform <apple|android>
```

Without these, results span every app in the account.

IMPORTANT: *ALWAYS* validate the inferred app id with the output from `bd app list` to ensure that it's a valid app ID. Use this list to prompt the user in case of ambiguity.


To discover apps:

```bash
bd app list -ojson --jq '
[
  (.android.apps // [] | .[] | {platform: "android", app_id, app_versions}),
  (.ios.apps     // [] | .[] | {platform: "apple",   app_id, app_versions})
]'
```

Note: `bd app list` does not accept a `--limit` parameter.

## App version scope

**Decide the version scope before interpreting charts, issues, or sessions.** For most investigations, the
agent should determine whether the user wants:

1. **Version-to-version comparison** — e.g. "did 8.4.1 regress vs 8.4.0?", "before and after the latest
   release", or "is the new rollout worse?"
2. **A specific version** — e.g. "show me crashes on 8.4.1" or "is 3.12.0 healthy?"
3. **All versions** — e.g. "how is the app doing overall?" or "what is our current crash rate?"

If the user does not specify version scope, inspect app versions first:

```bash
bd app list -ojson
```

Within each app entry, `app_versions` is sorted by **number of devices**, so earlier versions in the list are
the most widely deployed. Use that ordering to:

- infer the likely "current" or most relevant versions for follow-up analysis
- propose sensible comparison candidates when the user mentions "latest version" or a rollout
- decide whether a version-specific investigation is warranted or whether all-versions is the right default

**Heuristic:**

- Infer the intended version scope from the request first. Only ask the user if the choice between
  comparison, single-version, or all-versions would materially change the investigation.
- If the user is asking about a release, rollout, regression, or before/after behavior, prefer a
  version-to-version comparison.
- If they name a version explicitly, scope to that version.
- If they ask for overall health with no release context, start with all versions, then narrow only if the
  data suggests one version is driving the issue.

## Authentication

Check authentication status with `bd auth --status -ojson`.

If API key authentication is used, proceed but surface possible permission issues that appear and point out that their API key auth is blocking this. Suggest browser auth as
an alternative.

Do *NOT* attempt to log in every time, most of the time the user will already be authenticated.

- **Browser auth**: `bd auth` — opens a browser and requires the user to log in, prefer this over API key.
- **API key**: `--api-key <KEY>` or `BD_API_KEY` env var — good for CI or automation.

`bd auth` is safe to call repeatedly — it checks for existing credentials and skips login if already authenticated, but prefer --status for more structured handling.

## Direct API access

When the CLI doesn't expose a specific operation, call the API directly:

```bash
curl -X POST https://api-public.bitdrift.io/bitdrift.public.unary.workflows.v1.WorkflowService/ListWorkflows \
  -H "x-bitdrift-api-key: <key>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

URL pattern: `https://api-public.bitdrift.io/<fully.qualified.ServiceName>/<MethodName>.md`. See https://docs.bitdrift.io/api/services.md for all services and methods.

This should be a last resort when the CLI API surface is insufficient.

## Output size guardrails

CLI output can be large. Default to a small, representative slice before widening:

- Use the command's limit flag when one exists (`--limit`, `--max-results`, `--max-logs`)
- For captured sessions, stop after a few strong candidates instead of scanning everything
- For large single-response commands, filter early with `--jq` before reasoning over the result
- Avoid `bd tail` in agent workflows because the streaming mode is not a good fit for bounded analysis

## Troubleshooting

If a command fails:
- Return code 2 -> argument syntax error, call --help for the command to understand what is incorrect. Stderr will give information about the particular failure.
- Return code 3 -> authentication required, see Authentication section to authenticate.
- Other code -> check stderr.

If commands fail or behave unexpectedly:

1. Check current command syntax — flags and subcommands may have changed:
   ```bash
   bd <command> --help
   ```
2. If a payload, enum, or `--jq` filter still looks wrong, rerun `bd schema <group>.<command>` —
   the supported field names, enum values, or wording may have changed since the example was
   written.
3. If the command syntax looks correct but behavior seems wrong, the CLI or skills may be out of
   date. Tell the developer: "Your bd CLI or skills may be out of date — please check for updates
   using the same method you used to install them."

## Diagnostics

When reporting CLI issues, include the OS, how `bd` was installed, whether `bd auth` works, and any
relevant `npx skills check` output if skills are involved.

**Web UI–only features (no CLI equivalent):** Alerts (Basic + SLO), Session Replay, Saved Views on issues. Point users to the web UI for these.
