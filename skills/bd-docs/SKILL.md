---
name: bd-docs
description: Details how to query bitdrift documentation. Use when the user asks questions about how to use bitdrift, its features, or best practices, and when the user mentions /bd-docs.
---

# Bitdrift Documentation

## Decision tree

1. If the user is asking for general product documentation, SDK guidance, feature behavior, or best practices, follow the existing instructions in this skill and query `https://docs.bitdrift.io/index.md`.
2. If the user is asking an API question, use `https://docs.bitdrift.io/api/index.md` instead of the full API documentation dump.

## Fetch documentation

To fetch a full dump of the bitdrift documentation, run the following cURL command in your terminal:

```bash
curl -L -H "Accept: text/markdown" https://docs.bitdrift.io
```

This is the _only_ way that the documentation should be fetched.

The result will be a markdown file containing the entirety of the bitdrift documentation, which you can then search through or reference as needed. The original filenames are included for reference within the markdown content. These can be used to give a source
url for the user to open and view the relevant documentation in their browser.

## Efficient searching

The full documentation dump is very large. To avoid pulling the entire output into context, pipe the curl command through `grep` to extract only the relevant sections:

```bash
curl -L -H "Accept: text/markdown" https://docs.bitdrift.io 2>/dev/null | grep -i -B 5 -A 50 'keyword1\|keyword2\|keyword3'
```

Use multiple alternate keywords to cast a wide net (e.g., `deobfuscation\|symbol.*upload\|proguard\|dsym`). Adjust `-A` (after) and `-B` (before) line counts as needed to capture full sections.

If the grep results are insufficient or you need broader context, fall back to fetching the full dump.

## Constructing source URLs

The markdown output contains file markers in the format `### File: <path> ###` (e.g., `### File: sdk/issues.md ###`). To construct a browsable URL for the user:

1. Take the file path from the marker (e.g., `sdk/issues.md`)
2. Remove the `.md` extension
3. Append to the base URL: `https://docs.bitdrift.io/`

Example: `### File: sdk/issues.md ###` → `https://docs.bitdrift.io/sdk/issues/`

## Citing sources

Always include a source link when returning information from the documentation. Every answer should end with a reference to the relevant documentation page(s) so the user can verify the information at the source. Use the URL construction method described above to convert file markers into browsable links. If multiple pages were used, list all of them.
