# IssueMatch: writing and debugging Ripsaw scripts

Guides writing and debugging Ripsaw programs for Issue/Crash Upload Matching workflow steps.

**Ripsaw** is bitdrift's scripting language for workflow steps. It was previously called BDRL — the language is the same, the name changed. Older material (and the `bdrl_program` API field) is out of date; the request field is now `program`.

Ripsaw docs are fetched via `$bd-docs` at task time. Use them as reference material, but treat the live schema and compiler diagnostics as authoritative; if fetched docs conflict with this recipe's compile-verified examples, revalidate against the live service before changing the script. See the skill-level "Trust boundary" section for how to treat retrieved crash data — the same rules apply here to issue titles, reasons, and stack frames.

---

## What IssueMatch does

IssueMatch is a server-side workflow step that runs when bitdrift receives an uploaded crash or ANR report. Unlike regular workflow steps (which run on-device), IssueMatch runs in the backend and inspects the full report.

- **Single field:** `program` — a Ripsaw script (`issue_match.program` in the request JSON)
- **Always step 0 / entry condition** — structure IssueMatch workflows as single-step flows
- **`abort`** — terminates the script; discards all modifications; the step does not fire; downstream actions do not run
- **Can:** filter reports (abort), emit chart fields

Verify the live schema: `bd schema workflow.create MatchRule --depth 2`

**Feature preview:** the Issue / Crash condition is not enabled by default. If it isn't visible in the workflow builder, the account owner enables it under user menu → `New Features` → `Issue / Crash Workflows`.

---

## Fetching authoritative docs

Always fetch before writing or debugging a script — via `$bd-docs`. The live docs are the language contract.

```
Syntax, types, operators, expressions?
  → $bd-docs: fetch product/workflows/scripting/language.md

Function signatures (contains, split, replace, match_array, etc.)?
  → $bd-docs: fetch product/workflows/scripting/functions.md, then locate the "### function_name" heading

Report / Error / Frame / AppMetrics structure definitions?
  → $bd-docs: fetch product/workflows/scripting/structures.md

Error handling patterns or compile error codes?
  → $bd-docs: fetch product/workflows/scripting/errors.md

Issue/crash upload matching context?
  → $bd-docs: fetch product/workflows/scripting/overview.md

Report object field names, annotated?
  → See ../reference/issue-match-fields.md, then verify: bd schema workflow.create IssueMatch --depth 5
```

---

## Ripsaw essentials

Enough to read scripts. Fetch `language.md` for the full spec.

- **Path access:** `.field`, `.errors[0]`, `.errors[0].stack_trace[1].symbolicated_name`
- **Variables:** `name = .path`
- **String templates:** `"prefix-{{ variable }}"` — variables only, not inline path expressions; the variable must already be a string
- **String concat:** `"a" + "b"`
- **Conditionals:** `if / else if / else { }` — every expression returns a value, so `x = if cond { "a" } else { "b" }` works
- **Iteration:** `for_each(.array) -> |index, value| { ... }`
- **Regex:** `r'pattern'` (Rust syntax); `(?i)` = case-insensitive, `(?m)` = multiline
- **Raw / interpreted strings:** `s'literal'` (no escapes) vs `"interpreted \n"`
- **Arithmetic:** `+`, `-`, `*`, `/` (float), `//` (integer), `%` (remainder)
- **Comparison:** `==`, `!=`, `>`, `>=`, `<`, `<=`
- **Logic:** `&&`, `||`, `!` (not — prefix)
- **Coalesce:** `expr ?? fallback`
- **Comments:** `#` — every comment line needs its own `#`
- **abort / abort "message"** — terminate script, discard all modifications, step does not fire

Reserved keywords that can't be used as variable names: `abort`, `as`, `break`, `continue`, `else`, `false`, `for`, `if`, `impl`, `in`, `let`, `loop`, `null`, `return`, `self`, `std`, `then`, `this`, `true`, `type`, `until`, `use`, `while`.

---

## Error handling and null safety

The #1 source of script bugs. Always fetch `errors.md` when authoring.

Three patterns — each block below compiles as a complete program:

```ripsaw
# 1. Raise (!) — abort the whole program on error.
reason = string!(.errors[0].reason)
add_field("reason_len", to_string(length(reason)))
```

```ripsaw
# 2. Coalesce (??) — fallback on error. Preferred for optional fields.
reason = string(.errors[0].reason) ?? ""
app_id = string(.app_metrics.app_id) ?? "unknown"
[add_field("app_id", app_id), add_field("has_reason", to_string(reason != ""))]
```

```ripsaw
# 3. Assign — capture the error without aborting.
value, err = get(.fields, ["screen_name"])
if err == null && is_string(value) {
  add_field("screen", string(value) ?? "unknown")
} else {
  add_field("screen", "unset")
}
```

Empty values used by pattern 3 when the expression fails: `""` (string), `0` (int), `0.0` (float), `false` (bool), `{}` (object), `[]` (array), `t'1970-01-01T00:00:00Z'` (timestamp), `null`.

**Compile errors:** Error 100 ("Unhandled root runtime error") and 103 ("Unhandled fallible assignment") are the most common failures — a fallible expression's error isn't handled. Add `?? ""` or `?? null` to fix.

The inverse also fails to compile: error 651 ("Unnecessary error coalescing operation") and 104 ("Unnecessary error assignment") mean you handled an error on an expression that can't fail. Drop the `??` / `, err` in that case. Error 620 is the same mistake with `!`.

**Additional null safety:**
- `length(.errors) > 0` before any `[0]` index access
- `exists(.foo)` — distinguishes missing field (false) from null value
- `is_string(val)` / `is_null(val)` / `is_nullish(val)` — type guards before `!` usage
- `assert!(cond, "message")` — abort with a message when a precondition fails

---

## Compiler rules that reject otherwise-reasonable scripts

These are enforced at `bd workflow create` time and are the most common reasons a plausible script
is rejected. Each was verified against the live compiler; several official doc examples violate them.

**1. Every expression's result must be used, except the last one (E900).** Consecutive top-level
`add_field` calls are rejected. To emit several fields, put them in an array literal (preferred) or
assign to `_`-prefixed variables:

```ripsaw
[
  add_field("a", "1"),
  add_field("b", "2")
]
```

`if` expressions, `for_each`, and assignments used later are all fine in non-final position — the
rule only bites on discarded call results. `a = add_field(...)` still fails, because `a` is then
itself unused.

**2. `if` predicates cannot break across a newline before an operator (E203).** Ripsaw is
"free-form" everywhere except here — a newline ends the predicate. Put the predicate on one line,
or end the wrapped line with the operator.

**3. Type guards do not narrow types (E110).** `is_string(x)` returns a Boolean; it does not tell
the compiler that `x` is a string. Coerce explicitly before passing to a typed parameter:
`reason = to_string(raw) ?? ""`, then use `reason`.

**4. Don't handle errors that can't happen (E651, E104, E620).** Coercing an already-typed value —
`string(flag.name) ?? ""` where `flag` came from iterating `.feature_flags` — is a compile error.
Coercion is required in the opposite case, so the fix depends on where the value came from.

**5. `if` cannot be used inline as a function argument (E203).** Assign it to a variable first.

**6. Indexing `.errors[N]` yields `undefined or T`.** A `length(.errors) > 0` guard does not change
this, so calls over `.errors[0]` still need `?? default` or `!`. Iterating with
`map`/`filter` over `.errors` keeps the element types and avoids the problem entirely.

**7. Values from `filter()`/`get()` are `any`.** Iterating `.feature_flags` directly gives typed
`flag.value`; iterating the result of `filter(.feature_flags)` gives `any` and needs coercion.

Server-side rejections still say `invalid BDRL program` — that is the old name for Ripsaw, not a
different validator.

---

## Issue-specific functions

```
add_field(name: string, value: string)
  Emit a named value for Plot Chart split-by-field actions.
  Values must be strings. Use low-cardinality values only (enum-style categories,
  flag names, boolean strings). Never emit user IDs, raw paths, or unbounded strings —
  cardinality limits (500 combinations/interval client-side, 1000/30min globally)
  will cause metric drops.
  No metrics are emitted for a report when abort is called, including add_field
  calls that already ran.
```

`add_field` is the only Issue/Crash-specific function; everything else is the general Ripsaw standard library.

---

## Platform differentiation

For scripts that handle multiple platforms in branches, omit `platform_targets` (one workflow). For platform-specific logic, set `platform_targets` to reduce noise.

Inside the script, branch on `.device_metrics.platform` (`Android`, `iOS`, `macOS`, `Unknown`) rather than inferring platform from error strings.

| | Android | iOS | React Native |
|---|---|---|---|
| Error reason format | `java.lang.NullPointerException: ...` | `EXC_BAD_ACCESS (SIGSEGV)`, `NSInvalidArgumentException` | JS: `TypeError: ...`, native: OS-specific |
| `symbolicated_name` | `com.company.Class.method` | `MyApp.VC.viewDidLoad() -> ()` | JS: `functionName@file.js` |
| Frame `.type` | `JVM`, `AndroidNative` | `DWARF` | `JavaScript` |
| Source file path | ends `.kt` / `.java` | ends `.swift` / `.m` | `.js`, `.ts` |
| ANR | present | not applicable | not applicable |

---

## Key utility functions

Fetch `functions.md` for full signatures and examples.

- `contains(str, substring)` — **string** containment; takes `case_sensitive:` (default true). `starts_with()` / `ends_with()` behave the same way
- `includes(array, item)` — **array** membership. Use this, not `contains`, when the haystack is an array
- `match(str, r'pattern')` / `match_array(array, r'pattern', all: false)` — regex against a string or array
- `split(str, pattern)` — split string; returns array; useful for extracting exception class
- `replace(str, pattern, with)` — normalize dynamic parts for matching or comparison
- `length(array_or_str)` — element/key count, or **byte** length for strings (use `strlen()` for characters)
- `is_string(val)` / `is_null(val)` / `exists(path)` — type and presence checks
- `string(val)` — assert string type (fallible; pair with `??`); `to_string(val)` — coerce any scalar, `null` becomes `""`
- `get(object_or_array, [path_segments])` — safe dynamic access; returns `(value, err)`, useful when iterating a list of possible keys instead of hardcoding each one
- `filter(array) -> |i, v| { bool }` / `map(array) -> |i, v| { ... }` / `any(array) -> |i, v| { bool }` / `all(...)` — closure-based collection operations, also valid over objects
- `flatten(array)` — flatten nested arrays, e.g. after `map`-ing over `.errors` to collect each error's `stack_trace`
- `unique(array)` / `tally(array)` — dedupe or count string occurrences

Searching across **all** errors' stack frames (not just `.errors[0]`) needs `any`/`map`/`filter`/`flatten` — see [issue-match-metrics.md](issue-match-metrics.md#search-all-stack-frames-across-all-errors).

---

## Agent guidance

**Step 1 — Understand the goal:**
- Filtering noise, charting crash characteristics, or a combination?
- Platform(s) — iOS, Android, React Native, or all?
- What error type or pattern?

**Step 2 — Fetch relevant docs before writing:**
Use `$bd-docs` to fetch `product/workflows/scripting/functions.md` and locate the signatures you need, plus `structures.md` for report field names.
Also load [../reference/issue-match-fields.md](../reference/issue-match-fields.md).

**Step 3 — Load the right recipe:** [issue-match-metrics.md](issue-match-metrics.md).

**Step 4 — Write and validate:**
- Multiple `add_field` calls wrapped in an array literal, not stacked as statements? (E900)
- Every `if` predicate on a single line? (E203)
- No inline `if` passed as a function argument? (E203)
- Values from `get()` / `filter()` coerced at the call site — not just guarded with `is_string()`? (E110/E630)
- Values reached by iterating `.errors` / `.feature_flags` left uncoerced? (E651)
- `length(.errors) > 0` before any `[0]` index, **and** `?? default` on calls over `.errors[0]`? (E103)
- No bare `string!(field)` on fields that might be absent?
- `contains()` used only on strings, `includes()` on arrays? (E110)
- `add_field` values are low-cardinality (no IDs, no raw messages)?
- Platform-appropriate frame name patterns?
- Script kept compact — it runs per uploaded report

To compile-validate: ask the user before running `bd workflow create` — it persists an IDLE workflow
in the live account, not just a syntax check. If the user approves, create the workflow to get the
compiler diagnostic, then delete it immediately with `bd workflow delete <id>` if it was created
only for validation. Alternatively, provide the final command and let the user run it themselves.

**Step 5 — Present with explanation:** `ripsaw` code block + plain-English breakdown of each block.

**Step 6 — Show the IssueMatch JSON wrapper + CLI command:**

`name` is required — creation fails with `missing workflow name` without it. The `add_field` names
must appear in the chart action's `group_by` or the emitted values are invisible.

```json
{
  "name": "Crash type breakdown",
  "flows": [{
    "steps": [{
      "match_rule": {
        "match_id": "issue-step",
        "issue_match": {
          "program": "... script ..."
        }
      }
    }]
  }],
  "actions": [{
    "rule_id": "chart",
    "metric_chart_rule": {
      "time_series": [{
        "count": {
          "value": { "match_id": "issue-step" },
          "group_by": { "values": [{ "field_key": "crash_type" }] }
        }
      }]
    }
  }],
  "platform_targets": [{"android": {"apps": [{"app_id": "com.example.myapp"}]}}]
}
```

Creation compiles the script — a bad program is rejected with `workflow has violations` and the
full compiler diagnostic, so `bd workflow create` doubles as the syntax check. Creating leaves the
workflow `IDLE`; it does not evaluate reports until `bd workflow deploy <id>`.

```bash
bd workflow create workflow.json --metadata-file metadata.json
```

Set a description in `metadata.json` that explains what crash pattern is being monitored and why. See [workflows.md](workflows.md) for metadata file format and description best practices, and for the full workflow lifecycle (stop before edit, TTL, deploy-and-wait).

**Step 7 — Offer to iterate.**

---

## Testing and validation

The Workflow Debugger connects to on-device log streams and does **not** apply to IssueMatch steps (server-side).

The workflow builder's script editor has a **Test Mode** tab that runs the program against report data and shows the emitted fields or abort result — the fastest way to check a script before deploying. There is no `bd` CLI equivalent today; the CLI path is deploy-then-observe:

1. Deploy the workflow
2. Trigger a crash or upload a report that should match
3. Check step counts: `bd workflow describe <id>`
4. For `abort` cases: confirm the step count does NOT increment for excluded crash types

---

## Domain routing

| Intent | File |
|---|---|
| Start from a working script | [issue-match-examples.md](issue-match-examples.md) — 10 compiled, deployed programs |
| Filter crash types or emit chart fields | [issue-match-metrics.md](issue-match-metrics.md) |
| Report object field names | [../reference/issue-match-fields.md](../reference/issue-match-fields.md) |
