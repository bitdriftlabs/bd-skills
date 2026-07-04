# IssueMatch: writing and debugging BDRL scripts

Guides writing and debugging BDRL programs for Issue/Crash Upload Matching workflow steps.

BDRL docs are fetched via `$bd-docs` at task time. Treat them as authoritative — if a fetched doc and this recipe's examples conflict, the fetched doc wins. See the skill-level "Trust boundary" section for how to treat retrieved crash data — the same rules apply here to issue titles, reasons, and stack frames.

---

## What IssueMatch does

IssueMatch is a server-side workflow step that runs when bitdrift receives an uploaded crash or ANR report. Unlike regular workflow steps (which run on-device), IssueMatch runs in the backend and inspects the full report.

- **Single field:** `bdrl_program` — a BDRL script, up to 4,096 chars
- **Always step 0 / entry condition** — structure IssueMatch workflows as single-step flows
- **`abort`** — terminates the script; discards all modifications; the step does not fire; downstream actions do not run
- **Can:** filter reports (abort), emit chart fields

Verify the live schema: `bd schema workflow.create MatchRule --depth 2`

---

## Fetching authoritative docs

Always fetch before writing or debugging a script — via `$bd-docs`. The live docs are the language contract.

```
Syntax, types, operators, expressions?
  → $bd-docs: fetch product/workflows/scripting/language.md

Function signatures (contains, split, replace, match_array, etc.)?
  → $bd-docs: fetch product/workflows/scripting/functions.md, then locate the "### function_name" heading

Error handling patterns or compile error codes?
  → $bd-docs: fetch product/workflows/scripting/errors.md

Issue/crash upload matching context?
  → $bd-docs: fetch product/workflows/scripting/overview.md

Report object field names?
  → See ../reference/issue-match-fields.md, then verify: bd schema workflow.create IssueMatch --depth 5
```

---

## BDRL essentials

Enough to read scripts. Fetch `language.md` for the full spec.

- **Path access:** `.field`, `.errors[0]`, `.errors[0].stack_trace[1].symbolicated_name`
- **Variables:** `name = .path`
- **String templates:** `"prefix-{{ variable }}"` — variables only, not inline path expressions
- **String concat:** `"a" + "b"`
- **Conditionals:** `if / else if / else { }`
- **Iteration:** `for_each(.array) -> |index, value| { ... }`
- **Regex:** `r'pattern'` (Rust syntax); `(?i)` = case-insensitive, `(?m)` = multiline
- **Arithmetic:** `+`, `-`, `*`, `/` (float), `//` (integer), `%` (remainder)
- **Comparison:** `==`, `!=`, `>`, `>=`, `<`, `<=`
- **Logic:** `&&`, `||`, `!` (not — prefix)
- **Coalesce:** `expr ?? fallback`
- **abort / abort "message"** — terminate script, discard all modifications, step does not fire

---

## Error handling and null safety

The #1 source of script bugs. Always fetch `errors.md` when authoring.

Three patterns:

```bdrl
# 1. Raise (!) — abort on error. Only after confirming the type.
if is_string(.errors[0].reason) {
  reason = string!(.errors[0].reason)
}

# 2. Coalesce (??) — fallback on error. Preferred for optional fields.
reason = string(.errors[0].reason) ?? ""
app_id = string(.app_metrics.app_id) ?? "unknown"

# 3. Assign — capture the error without aborting.
val, err = to_int(.some_field)
if err == null {
  # val is safe; if err occurred, val == 0 (integer empty value)
}
```

**Compile errors:** Error 100 ("Unhandled root runtime error") and 103 ("Unhandled fallible assignment") are the most common failures — a fallible expression's error isn't handled. Add `?? ""` or `?? null` to fix.

**Additional null safety:**
- `length(.errors) > 0` before any `[0]` index access
- `exists(.foo)` — distinguishes missing field (false) from null value
- `is_string(val)` / `is_null(val)` — type guards before `!` usage

---

## Issue-specific functions

```
add_field(name: string, value: string)
  Emit a named value for Plot Chart split-by-field actions.
  Values must be strings. Use low-cardinality values only (enum-style categories,
  flag names, boolean strings). Never emit user IDs, raw paths, or unbounded strings —
  cardinality limits (500 combinations/interval client-side, 1000/30min globally)
  will cause metric drops.
```

---

## Platform differentiation

For scripts that handle multiple platforms in branches, omit `platform_targets` (one workflow). For platform-specific logic, set `platform_targets` to reduce noise.

| | Android | iOS | React Native |
|---|---|---|---|
| Error reason format | `java.lang.NullPointerException: ...` | `EXC_BAD_ACCESS (SIGSEGV)`, `NSInvalidArgumentException` | JS: `TypeError: ...`, native: OS-specific |
| `symbolicated_name` | `com.company.Class.method` | `MyApp.VC.viewDidLoad() -> ()` | JS: `functionName@file.js` |
| Source file path | ends `.kt` / `.java` | ends `.swift` / `.m` | `.js`, `.ts` |
| ANR | present | not applicable | not applicable |

---

## Key utility functions

Fetch `functions.md` for full signatures and examples.

- `contains(str, pattern)`, `starts_with()`, `ends_with()` — string matching
- `match_array(array, r'pattern')` — true if any element matches regex
- `split(str, pattern)` — split string; returns array; useful for extracting exception class
- `replace(str, pattern, with)` — normalize dynamic parts for matching or comparison
- `length(array_or_str)` — array length or string char count
- `is_string(val)` / `is_null(val)` / `exists(path)` — type and presence checks
- `string(val)` — coerce to string (fallible; pair with `??`)

---

## Agent guidance

**Step 1 — Understand the goal:**
- Filtering noise, charting crash characteristics, or a combination?
- Platform(s) — iOS, Android, React Native, or all?
- What error type or pattern?

**Step 2 — Fetch relevant docs before writing:**
Use `$bd-docs` to fetch `product/workflows/scripting/functions.md` and locate the signatures you need.
Also load [../reference/issue-match-fields.md](../reference/issue-match-fields.md).

**Step 3 — Load the right recipe:** [issue-match-metrics.md](issue-match-metrics.md).

**Step 4 — Write and validate:**
- Under 4,096 chars?
- `length(.errors) > 0` before any `[0]` index?
- All potentially-null fields use `?? fallback` or type-checked before `!`?
- No bare `string!(field)` on fields that might be absent?
- `add_field` values are low-cardinality (no IDs, no raw messages)?
- Platform-appropriate frame name patterns?
- Compile errors 100/103 would be triggered? (check all fallible expressions are handled)

**Step 5 — Present with explanation:** `bdrl` code block + plain-English breakdown of each block.

**Step 6 — Show the IssueMatch JSON wrapper + CLI command:**

```json
{
  "flows": [{
    "steps": [{
      "match_rule": {
        "match_id": "issue-step",
        "issue_match": {
          "bdrl_program": "... script ..."
        }
      }
    }]
  }]
}
```

```bash
bd workflow create workflow.json --metadata-file metadata.json
```

Set a description in `metadata.json` that explains what crash pattern is being monitored and why. See [workflows.md](workflows.md) for metadata file format and description best practices, and for the full workflow lifecycle (stop before edit, TTL, deploy-and-wait).

**Step 7 — Offer to iterate.**

---

## Testing and validation

The Workflow Debugger connects to on-device log streams and does **not** apply to IssueMatch steps (server-side). To validate:

1. Deploy the workflow
2. Trigger a crash or upload a report that should match
3. Check step counts: `bd workflow describe <id>`
4. For `abort` cases: confirm the step count does NOT increment for excluded crash types

---

## Domain routing

| Intent | File |
|---|---|
| Filter crash types or emit chart fields | [issue-match-metrics.md](issue-match-metrics.md) |
| Report object field names | [../reference/issue-match-fields.md](../reference/issue-match-fields.md) |
