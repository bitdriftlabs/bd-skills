# Session Replay

Use `bd timeline replay` to retrieve and decode Session Replay wireframes from a session. The
command selects only replay logs whose message is exactly `Screen captured`, decodes their packed
screen payload, and handles pagination.

If the installed CLI does not list `timeline replay` or `replay decode`, update to a `bd` release
that includes those commands.

## Start with an aggregate

For a compact view of a session's replay coverage, decoded geometry, and screen context:

```bash
bd timeline replay <session_id> -o json --summary --screen-context
```

`--screen-context` associates frames with the nearest preceding `ScreenView` event when the app
emits one. It is optional context: replay works without Screen View instrumentation, and an absent
screen name is not a replay failure.

Without `--max-results`, the command paginates through the selected replay logs. If you set that
flag, treat the result as a bounded slice rather than the complete replay.

## Inspect individual frames

Use per-frame summaries to compare timestamps, screen names, rectangle counts, inferred bounds,
and view types without returning every rectangle:

```bash
bd timeline replay <session_id> -o jsonl --frame-summary --screen-context
```

Omit `--frame-summary` when a task needs the decoded rectangles themselves. Use `--query`,
`--field`, `--log-level`, or a time range to narrow the replay selection when appropriate.

## Decode supplied payloads

For Base64 payloads obtained outside a session timeline, use the local decoder; it does not contact
the API:

```bash
printf '%s\n' '<base64_payload>' \
  | bd replay decode -o jsonl --input - --frame-summary
```

Use `--payload <base64_payload>` for one value, or `--binary-input <path>` for a raw packed
payload. Omit `--frame-summary` when rectangles are needed.

## Output reference

Use the CLI schema for the current, versioned output contract instead of reimplementing the packed
wire format:

```bash
bd schema timeline.replay output
bd schema replay.decode output
```

Both commands expose `ReplayFrame` records. Frame summaries include decoded geometry statistics;
session summaries also include aggregate frame counts, bounds, view types, and screen-context
counts. `inferred_bounds` is the maximum rectangle extent, not the device viewport; rectangles may
extend beyond the visible screen.

## Partial or failed captures

For a suspicious frame, inspect its `error` and `exception_causing_view_count`. A nonzero exception
count means the SDK skipped a view and its children during capture, so that frame may be partial.
The aggregate summary reports this as `partial_frames` and `skipped_view_count`; check those fields
when the replay appears sparse or inconsistent rather than as a requirement for every replay.
