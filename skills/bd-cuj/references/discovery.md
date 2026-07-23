# Phase 0: Discovery

Work through the following steps in order. Do not deploy anything until the user approves the final summary.

---

## Step 1 — Instrumentation gate

Ask the user:

> "Is the app already instrumented with the bitdrift SDK — does it call `Logger.start()` (iOS/Android) or `Capture.start()` (React Native)?"

- **Yes** → continue.
- **No or unsure** → stop and say: "Let's get the SDK set up first — I can walk you through that with `$bd-instrumentation`."

---

## Step 2 — Confirm app IDs

Run `bd app list` to discover available apps and platforms:

```bash
bd app list
```

Present the list and ask the user which app(s) this CUJ applies to. Note the `app_id` and `platform` for each — these go into every workflow's `platform_targets`.

---

## Step 3 — Example sessions

Ask:

> "Can you share a session ID where a user successfully completed this journey, and ideally one where a user abandoned or failed it? I'll inspect the actual log events to identify the right field names rather than guessing."

For each session ID provided, hydrate and fetch the logs:

```bash
bd timeline hydrate {{SESSION_ID}} --poll-interval-seconds 2
bd timeline logs {{SESSION_ID}} -o jsonl | head -100
```

> `bd timeline logs` prints status lines to stderr; the JSON output on stdout stays clean. If the first attempt returns nothing, retry without `-o jsonl` to see raw output and confirm the session hydrated successfully.

Scan the output for events that look like CUJ steps — custom field/value pairs, screen view events, or log messages that correspond to meaningful moments in the journey. Ignore low-level SDK events (network responses, ANR frames, crash frames) unless the user is specifically interested in them.

Present a condensed list of candidate events from the success session:

> "Here are the events I see in the success session that look like CUJ steps. Do any of these correspond to the steps you want to monitor?"

If a failure session was provided, compare it against the success session:

> "In the failure session, the journey appears to stop at [event]. Does that match the drop-off point you'd expect?"

Use what you learn to pre-populate the field names and values in Step 5. The user confirms — you do not assume.

> **If no session IDs are available:** proceed without them, but note that field names and values in Step 5 will need to be provided manually and should be verified against `bd tail` output before deploying.

---

## Step 4 — CUJ name and steps

Ask:

> "What is the name of this journey? (e.g. Checkout, Onboarding, Login)"

Then, based on what you found in the sessions (or asking the user directly if no sessions were available):

> "Here are the step candidates I identified from the session — does this look like the right set, and is the order correct? Add, remove, or rename any steps before we continue."

If no session was provided, ask:

> "Please list every step from start to finish. For each step provide:
> - A step name (e.g. 'Cart Viewed')
> - The exact identifier — screen name, field name + value, or log field name + value"

Wait for confirmation or corrections before proceeding.

---

## Step 4a — Step identifier type

Once steps are confirmed, **explicitly ask**:

> "Are all steps identified by screen names (bitdrift screen view events), analytics events, or log messages — or a mix? This determines the matcher type used in every workflow."

- **Screen names** → `ootb_match: SCREEN_VIEW` with `_screen_name`
- **Analytics events** → `generic_match` on the event field + value
- **Log messages** → `generic_match` on the log body field — use the exact field name seen in the session logs, never assume `message`

A mix is valid. Record the matcher type per step before continuing — it determines the workflow template used in all subsequent phases.

---

## Step 5 — Key step

Ask:

> "Which two consecutive steps form the most business-critical sub-span? This is the pair we'll measure duration on, alert when p95 is exceeded, and capture sessions for. (e.g. 'Payment Initiated → Payment Confirmed')"

Record the start step and end step of the key pair.

---

## Step 6 — CUJ scope field (optional)

Ask:

> "Is there a field on all logs emitted during this journey that can be used to scope matchers? (e.g. `cuj == 'checkout'` set via a FieldProvider) Leave blank if not applicable."

If provided, note the field name and value — add it as an additional matcher condition in all workflow steps.

---

## Step 7 — Network scope (optional)

Ask:

> "Do you want to monitor network requests during this journey? If yes, provide the production API hostname and any path templates you want to scope to (e.g. `api.example.com`, `/v1/checkout/confirm`). Leave blank to skip the Network tab."

If the user provides paths discovered from session logs, check whether the hostname looks like a local or emulator address (`localhost`, `127.0.0.1`, `10.0.2.2`, `10.0.3.2`):

> "The session shows requests going to `{{HOST}}` — that looks like a local/emulator address. What is the production API hostname?"

Do not proceed with network monitoring until a production hostname is confirmed.

If no paths are provided, ask:

> "Should I monitor all requests to `{{HOST}}`, or scope to specific path templates?"

If skipped, note that Phase 3 and the Network dashboard tab will be omitted.

---

## Step 8 — Discovery summary

Echo back the full discovery as a table for approval before any deployment:

| Field | Value |
|---|---|
| **CUJ name** | `{{JOURNEY_NAME}}` |
| **Platform(s)** | `{{PLATFORMS}}` |
| **App ID(s)** | `{{APP_IDS}}` |
| **Identifier type** | `{{SCREEN / ANALYTICS EVENT / LOG}}` |
| **Steps (in order)** | Step 1: `{{NAME}}` — `{{FIELD}} == "{{VALUE}}"` |
| | Step 2: … |
| **Key step** | `{{KEY_STEP_START}}` → `{{KEY_STEP_END}}` |
| **CUJ scope field** | `{{FIELD}} == "{{VALUE}}"` (or none) |
| **Network host** | `{{HOST}}` (or skipped) |
| **Network paths** | `{{PATH_TEMPLATE_1}}`, … |

Ask:

> "Does everything look correct? I won't deploy anything until you confirm."

Once confirmed, proceed to [sankey.md](sankey.md).
