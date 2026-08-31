# Teams and Access Control

Use teams to manage reusable groups of organization members, then apply the same access policy to
workflows, saved views, and dashboards. Start from the resource you want to share; access updates
replace the resource's complete current access list.

## Teams

Discover the current team surface before acting:

```bash
bd teams --help
bd schema teams
```

Use `bd teams list --all -o jsonl --jq '{id, name}'` to find a team ID. Create or update a team with its name and
description, then add or remove member IDs with the membership subcommands. Treat team membership
changes as access changes: they immediately affect every resource shared with that team.

```bash
# Omit --team-id to create a team; include it to replace that team's name and description.
bd teams upsert --name "On-call" --description "Primary incident responders"
bd teams upsert --team-id <TEAM_ID> --name "On-call" --description "Primary incident responders"

# Repeat --user-id to change multiple members at once.
bd teams add-members <TEAM_ID> --user-id <USER_ID> --user-id <USER_ID>
bd teams remove-members <TEAM_ID> --user-id <USER_ID>
```

Before deleting a team, list resources it owns and transfer ownership. Do not rely on deletion to
quietly remove an ownership relationship.

## Setting access

The following commands deliberately use the same access inputs:

```bash
bd workflow access set <WORKFLOW_ID> ...
bd view access set <VIEW_ID> ...
bd dashboard access set <DASHBOARD_ID> ...
```

Run `--help` on the exact command to confirm the current flags. Use `bd schema` for the canonical
request and response shape before automating updates.

An access update names exactly one owner, organization access, individual grants, and team grants:

- Set exactly one of `--owner-user-id <USER_ID>` or `--owner-team-id <TEAM_ID>`.
- `--organization` accepts `view`, `edit`, or `none` and defaults to **`view`** when omitted. Pass
  `--organization none` to make the resource restricted to its explicit grants.
- Repeat `--user <USER_ID>=<view|edit|none>` and `--team <TEAM_ID>=<view|edit|none>` for explicit
  grants.

For example, this keeps the organization restricted, assigns a team owner, and grants one person
edit access:

```bash
bd workflow access set <WORKFLOW_ID> \
  --owner-team-id <OWNER_TEAM_ID> \
  --organization none \
  --user <EDITOR_USER_ID>=edit \
  --team <VIEWER_TEAM_ID>=view
```

The recommended workflow is:

1. Fetch the resource first (`bd workflow describe`, `bd view get`, or `bd dashboard get`) and
   inspect `current_access_permissions`.
2. Build the full replacement policy from that current state.
3. Apply it with the appropriate `access set` command.
4. Fetch the resource again and verify the returned access permissions.

### Permission rules

- Viewer: can open and list the resource.
- Editor: can open and edit its content, but cannot save access changes or delete it.
- Owner: can edit content, save access changes, and delete it.
- Organization access is Viewer, Editor, or Restricted. Restricted removes the organization-wide
  grant but retains explicit user and team grants.
- An explicit `none` grant overrides access inherited through the organization or a team.
- Multiple positive grants use the highest access level. Membership of the owner team grants owner
  access.

Workflow deployment still requires deployment permission in addition to resource access. Workflow
and dashboard administrators can manage access and delete their respective resources. User
Administrators can manage access and delete an accessible saved view, while content edits remain
access-controlled.

## Safe automation

Keep the full policy in source control or an auditable script. Do not derive a grant from a display
name: resolve and use immutable user and team IDs. After any concurrent access change, refetch the
resource because the last saved policy wins.
