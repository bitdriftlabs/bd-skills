# Reading Issues

Issues are crash reports and error events grouped by type. The hierarchy is: **issue group** (a crash type) → **issues** (individual occurrences). Most issues include a `session_id` for reading full session logs.

---

## JSON Output Shape

Use `bd schema issue.group.list --docs` and `bd schema issue.list --docs` for the full response
schemas and docs.

---

## Status Lifecycle

| Status | Meaning |
|---|---|
| `NEW` | Assigned automatically on first creation |
| `IN_PROGRESS` | Set manually during investigation |
| `FIXED` | Records the app version at time of marking |
| `REOPENED` | Applied **automatically** when a `FIXED` group gets a crash on a newer app version |
| `IGNORED` / `SNOOZED` | Suppressed from default views |

**Convenience groupings:** `Open` = NEW + IN_PROGRESS + REOPENED; `Closed` = FIXED + IGNORED

---

## Advanced Filtering with `--request-file`

For filters beyond `--app-id` and `--platform`, use `--request-file` with a protobuf JSON payload.
Use the schema docs to build the payload:

```bash
bd schema issue.group.list --docs
bd schema issue.group.list AdvancedFilter --docs
```

- `feature_flag_filters[].exclusive: true` — only crashes where the flag was **always** active
  (strong correlation)
- `feature_flag_filters[].exclusive: false` — crashes where the flag was active at least once
  (weaker signal)

---

## Triage Patterns

### Prioritizing crash groups

- **`NEW` + high count** → new regression, highest priority
- **`NEW` + low count** → may be emerging; watch but don't panic
- **`REOPENED`** → a fix didn't hold; investigate what changed
- **Single-platform** → check `platform` field; often platform-specific root causes

### Trend comparison

```bash
# Current 7 days
bd issue group list -o json --last 7d --all --app-id <BUNDLE_ID> --platform <PLATFORM> \
  --jq '[.issue_groups[] | ([.stats.events[].count | tonumber] | add)] | add'

# Previous 7 days
bd issue group list -o json \
  --since "$(date -u -v-14d +%Y-%m-%dT%H:%M:%SZ)" \
  --until "$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)" --all \
  --app-id <BUNDLE_ID> --platform <PLATFORM> \
  --jq '[.issue_groups[] | ([.stats.events[].count | tonumber] | add)] | add'
```

### Session jump

Every issue has a `session_id` — always note it and offer to read the full session timeline:

```bash
bd issue list <group_id> -o json --limit 5 \
  --jq '[.issues[] | {id, session_id, time}]'
```

---

## Pitfalls

| Mistake | Fix |
|---|---|
| Low crash count on a crash-loop | If a group shows 1 event in startup code, the app may be crash-looping — SDK sends reports on next successful launch, so rapid crash-on-startup loops underreport. Cross-check exit reasons (`6YYT`/`o30N`) — high exit rates with low crash counts = likely crash loop |
| Missing `session_id` on some issues | Not all issue types attach a session; check for null before calling `bd timeline` |

---

## Workflow-based Issue Processing

To filter uploaded crash reports or chart crash metrics using BDRL scripts, see `$bd-issue-match`.
