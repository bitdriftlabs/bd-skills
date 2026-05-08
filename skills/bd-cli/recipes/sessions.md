# Reading Session Timelines

Two common entry points:

1. **From a workflow** — you have a workflow with a `flush_rule` and want its captured sessions
2. **From a session ID** — you already have a session ID and want to inspect or search the timeline

---

## Captured Sessions from a Workflow

Use `bd schema workflow.captured-sessions --docs` for the response shape.

The most important field is usually `.fields`: it tells you which saved values or extracted fields
are associated with each captured session before you open the raw timeline.

If the workflow has no `flush_rule`, `captured-sessions` fails. Check the workflow actions first.

---

## Session Timeline

Use:

- `bd timeline search <session_id> ...` for focused event lookup anywhere in the session
- `bd timeline logs <session_id>` for full-session inspection and inventory

Both commands handle hydration for you before reading the timeline.
That is convenient for one session, but when you have many candidate sessions it can serialize the
wait. Use `bd timeline hydrate <session_id> --no-wait` to trigger hydration first across the whole
set, then come back with `timeline search` or `timeline logs` once sessions are ready.

Use schema for the live shape (`bd schema timeline.search --docs`, `bd schema timeline.logs --docs`,
`bd schema timeline.hydrate --docs`).

### Hydration behavior

- `HYDRATING` — still in progress; wait and retry
- `HYDRATED` — ready to read
- `FAILED` — unavailable; skip this session
- `NOT_FOUND` from timeline/hydration calls usually means the session ID is wrong or no hydration
  record exists yet

### Batch hydration without waiting

`bd timeline hydrate <session_id>` normally polls until hydration finishes. Add `--no-wait` when
you want to start hydration and return the current hydration state immediately.

This is useful when triaging many sessions: trigger hydration for all interesting session IDs first,
then read the ones that come back `HYDRATED` instead of blocking on each session one at a time.

```bash
# Trigger hydration for many sessions without waiting on each one.
while read -r session_id; do
  bd timeline hydrate --no-wait "$session_id" -o json --jq '.hydration_status' -r 2>/dev/null
done < session_ids.txt
```

If you want actual parallel request fan-out as well as non-blocking waits, use your shell tooling
(`xargs -P`, GNU parallel, etc.) around the same `--no-wait` pattern.

---

## Choosing What to Inspect

Session timelines explain concrete behavior within a session. For population-wide questions
(rankings, top-K, overall rates), prefer [charts](charts.md).

Prefer this order:

1. **Use the source context first** — issue reason, workflow trigger, captured-session `.fields`, or
   the symptom the user described
2. **If you already know the event family, start with `timeline search`** — use the narrowest
   reliable filter you already have (`--message`, `--log-type`, `--log-level`, `--field`)
3. **If you do not have a hypothesis, inventory the session** — summarize messages or log types to
   see what families of logs are present
4. **Then drill in** — inspect the relevant schema and refine with `--field` or `--request-file`

Useful inventory patterns (full timeline):

```bash
# Which messages are present most often?
bd timeline logs <session_id> -o json --jq '[.logs[].message] | group_by(.) | map({message: .[0], count: length}) | sort_by(-.count)'

# Which log types dominate?
bd timeline logs <session_id> -o json --jq '[.logs[].log_type] | group_by(.) | map({log_type: .[0], count: length}) | sort_by(-.count)'
```

This is usually enough to decide whether to focus on network, lifecycle, resource, replay, or
app-defined logs before writing narrower filters.

### `RESOURCE` logs

Use `--log-type resource` when you want per-session resource telemetry.

Typical fields include battery state/level, low-power mode, memory pressure, JVM/native memory
usage, and per-minute request/response byte counters.

```bash
# Show only resource telemetry for the session.
bd timeline search <session_id> --log-type resource

# See the documented RESOURCE field list and meanings.
bd schema workflow.create GenericOotbConditionType.RESOURCE --docs
```

---

## Reading Efficiently

Output caps (`--max-results`, `--max-logs`) return a bounded slice, not the full session. For
repeated analysis, save to a file first; check `.total_pages` to know if you truncated.

Use `--field key=value` for exact field matches and `--query` for broader contains-style search.

For OR across message families, run separate searches before reaching for `--request-file`.

Timeline message names and OOTB condition names do not always match. Non-obvious mappings:

| OOTB condition | `--message` value |
|---|---|
| `NETWORK_REQUEST` / `NETWORK_RESPONSE` | `HTTPRequest` / `HTTPResponse` |
| `APP_LAUNCH` | `AppCreate` (Android) or `AppFinishedLaunching` (iOS) |
| `APP_OPEN` | `AppStart`, `AppFinishedLaunching`, or `SceneWillEnterFG` |
| `APP_BACKGROUND` / `APP_FOREGROUND` | `AppPause` / `AppResume` (Android) or `SceneDidEnterBG` / `SceneWillEnterFG` (iOS) |
| `APP_TERMINATION`, crash/ANR | `AppExit` — narrow with enum-specific fields from `bd schema workflow.create <EnumType.VALUE>` |

To discover field keys on a candidate event, inspect the OOTB condition schema or search and
inspect the payload:

```bash
bd timeline search <session_id> --message HTTPResponse -o jsonl --jq '.log.fields | keys' 2>/dev/null
```

If the common flags are not expressive enough, switch to `--request-file`.

---

## Pitfalls

| Mistake | Fix |
|---|---|
| Calling `captured-sessions` on a workflow without a `flush_rule` | Check the workflow actions first |
| Bulk-hydrating many sessions | Hydrate sparingly; prefer sessions that are already ready |
| Treating capped output as complete (`--max-logs`, `--max-results`) | Caps are for bounded slices, not complete views |
| Using `timeline logs` + local `jq select(...)` for common exact/contains/field searches | Prefer `timeline search` so the server scans the whole session and returns match metadata |
| Piping timeline output without handling stderr | Status lines go to stderr; use `2>/dev/null` when they are noise |
