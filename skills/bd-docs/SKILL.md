---
name: bd-docs
description: "Search and interpret bitdrift documentation for product behavior, SDK setup, API and service docs, and best practices. Use whenever the user asks how bitdrift works, how to set up the SDK, how to configure a feature, what an API or service does, or for conceptual guidance about bitdrift — even if they do not explicitly mention documentation. Also trigger when the user mentions /bd-docs or asks about bitdrift concepts, architecture, or integration guides."
license: PolyForm Shield License 1.0.0
---

# Bitdrift Documentation

## Decision tree

1. **General product questions** (SDK setup, feature behavior, best practices) → fetch from `https://docs.bitdrift.io`
2. **API reference questions** (services, methods, request/response shapes) → fetch from `https://docs.bitdrift.io/api/index`
3. **Live field names, enum values, CLI request shapes** → defer to the bd-cli skill and `bd schema`; docs may lag behind the live API

## Fetching documentation

### Full documentation dump

```bash
curl -L -H "Accept: text/markdown" https://docs.bitdrift.io 2>/dev/null
```

This returns the entire bitdrift documentation as a single markdown file. The original filenames are included as `### File: <path> ###` markers.

### Targeted search (preferred for most questions)

The full dump is large. Pipe through `grep` to extract only relevant sections:

```bash
curl -L -H "Accept: text/markdown" https://docs.bitdrift.io 2>/dev/null | grep -i -B 5 -A 50 'keyword1\|keyword2\|keyword3'
```

Use multiple alternate keywords to cast a wide net. For example, for a deobfuscation question:
```bash
curl -L -H "Accept: text/markdown" https://docs.bitdrift.io 2>/dev/null | grep -i -B 5 -A 50 'deobfuscation\|symbol.*upload\|proguard\|dsym'
```

Adjust `-A` (after) and `-B` (before) line counts as needed to capture full sections.

### API documentation

For API-specific questions, fetch the API index:
```bash
curl -L -H "Accept: text/markdown" https://docs.bitdrift.io/api/index 2>/dev/null
```

Then drill into specific service docs as needed based on the index contents.

### Fallback strategy

If grep results are insufficient or you need broader context, fall back to fetching the full dump. If the docs don't answer the question or seem outdated, note this to the user and suggest checking `bd schema` via the bd-cli skill for the latest field names and API shapes.

## Constructing source URLs

The `Accept: text/markdown` header handles format negotiation — never append `.md` to URLs. The markdown output contains file markers like `### File: sdk/quickstart.md ###`; to turn one into a browsable URL, strip the `.md` extension and prepend the base URL. Do not add a trailing slash.

Example: `### File: sdk/quickstart.md ###` → `https://docs.bitdrift.io/sdk/quickstart`

## Citing sources

Always include source links when returning information from the documentation. Every answer should end with references to the relevant documentation page(s) so the user can verify at the source. If multiple pages were used, list all of them.

## Examples

| User question | Approach |
|---|---|
| "How do I set up the bitdrift SDK for iOS?" | Search for `sdk\|ios\|setup\|install\|cocoapods\|swift` |
| "What events does bitdrift capture automatically?" | Search for `ootb\|out.of.the.box\|automatic.*event\|built.in` |
| "What API services does bitdrift expose?" | Fetch `api/index` directly |
| "What fields does NETWORK_RESPONSE have?" | Defer to bd-cli skill (`bd schema workflow.create GenericOotbConditionType.NETWORK_RESPONSE`) |
| "What's the best practice for session replay?" | Search for `session.replay\|replay.*best\|replay.*practice` |
