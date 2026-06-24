# Entity Management

Entities are the bitdrift representation of a specific user (or device). An entity is identified by the hashed form of whatever string you pass to `Logger.setEntityID` / `setEntityId` in the SDK. The exact string is never stored — you query by it, but only the hash is persisted.

---

## Lookup by entity ID, hash, or device

```bash
# Look up by the raw ID your app passed to setEntityID
bd entity get <entity_id> --last 7d

# Look up by the obfuscated hash shown in the UI
bd entity get --entity-hash <hash> --last 7d

# Look up by device ID
bd entity get --device-id <device_id> --last 7d
```

The response includes everything needed to start an investigation:

- **`recent_sessions`** — up to 5 sessions by default (increase with `--max-recent-sessions`), ordered by `last_seen`. Each has a `session_id` to pass directly to `bd timeline logs` or `bd timeline search`.
- **`issue_summary`** — total crash count, last crash time, and top crash groups for this entity
- **`devices`** — all devices seen: platform, OS version, app version, first/last seen
- **`online_summary`** — last seen time and whether they're currently online

```bash
# Extract session IDs for the most recent sessions
bd entity get <entity_id> --last 7d -o json --jq '[.recent_sessions[].session_id]' -r
```

---

## No sessions and entity is offline

If `recent_sessions` is empty and the entity is not currently online, queue a recording for their next session:

```bash
# Queue a capture — fires the next time this entity comes online
bd entity record-next-online-time upsert <entity_id>

# Optionally notify a team channel when the recording completes
bd entity record-next-online-time upsert <entity_id> --notification-group <group-name>
```

The recording request lifecycle: `PENDING` → `RECORDED` (success) / `CANCELED` / `FAILED`.

Check status at any time:

```bash
bd entity record-next-online-time list -o json --jq '.entity_record_next_online_times[] | {entity: .entity_id.hash, status: .status}'
```

When the recording completes, bitdrift fires an `EntityRecordingCompletedNotification` webhook to any notification groups you attached. Use `bd notification-group list` to see available groups, or `bd notification-group upsert` to create one pointing at a Slack channel or webhook endpoint.

Once recorded, run `bd entity get <entity_id>` again — the new session will appear in `recent_sessions`.

---

## Known (bookmarked) entities

Bookmarking an entity lets you proactively monitor VIPs — executives, beta testers, high-value accounts — and use the `known_entity_match` workflow matcher to guarantee session capture for them.

```bash
# List all bookmarked entities, most recently viewed first
bd entity known list --sort-by VIEWED --desc

# Search by display name (fuzzy match)
bd entity known list --known-entity-name "CEO"

# Bookmark an entity
bd entity known upsert <entity_id> --name "Jane Smith"

# Remove a bookmark
bd entity known delete <entity_id>
```

The list response includes `last_seen` and `last_session_capture` per entity, so you can immediately triage whether there's been recent activity before pulling the full detail.

Once you have the entity hash from the list:

```bash
bd entity get --entity-hash <hash> --last 7d
```

See [workflow-schema.md](../reference/workflow-schema.md) for the `known_entity_match` workflow matcher, and [workflows.md](workflows.md) for the full VIP capture recipe.
