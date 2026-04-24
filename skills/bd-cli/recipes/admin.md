# Key & Connector Management

Manage API keys, SDK keys, and external connectors via the `bd` CLI.

Start with:

```bash
bd key --help
bd connector --help
bd schema key
bd schema connector
```

Use `--help` for current subcommands, flags, and accepted values. Use `bd schema` when you need the
request/response shape for a specific key or connector operation.

---

## API & SDK Keys

### API keys

Run `bd key create api --help` for the current permission enum list.

Use least privilege. Start from the specific operation the key needs to perform, then grant the
smallest permission set that satisfies that use case.

When answering an API-key creation request, make the final response cover all of these:

1. what you created
2. what the selected permissions allow
3. how the key should be stored safely

Do not stop at "here is the key" if the user also needs to understand the permission scope or safe
handling expectations.

When revoking a key, verify the ID first. Revoking the API key you are currently authenticated with
will lock you out.

### SDK keys

SDK keys are bound to app/bundle IDs by regex. Scope the regex narrowly to the app IDs you intend
to match. Avoid catch-all patterns such as `.*`.

Use `--app-id-postfix` when the SDK handshake app ID includes a suffix that should not be part of
the main regex (for example, debug or staging variants).

---

## Connectors

Use `bd connector --help` for the supported connector types and required flags.

For CloudWatch, the IAM role must allow bitdrift to assume it and write to the target CloudWatch
resources.

---

## Pitfalls

| Mistake | Fix |
|---|---|
| Revoking the key you're authenticated with | Confirm the key ID before revoking |
| Overly broad SDK key regex (e.g. `.*`) | Scope to the specific app ID pattern; broad regex matches unintended apps |
| Creating API keys with `workflow-admin` when only `workflow-read` is needed | Use minimum permissions — grant only what the use case requires |
| Forgetting `--name` on key creation | Name is optional but strongly recommended for identifying keys later |
