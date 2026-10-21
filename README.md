# bitdrift Agent Skills and Plugins

Agent skills and plugins for [bitdrift](https://bitdrift.ai) — mobile observability that stores telemetry on-device and uploads only what you need.

- **bd-cli** — CLI usage: workflows, charts, sessions, issues, admin
- **bd-instrumentation** - Installing and configuring the SDK to instrument iOS, Android, or React Native apps
- **bd-docs** — Fetch and search bitdrift documentation
- **bd-cuj** — Setting up end-to-end Critical User Journey monitoring: conversion funnels, step duration alerting, path discovery, dashboards

## Installation

Use your preferred distribution channel. Skills installers install the skills above directly;
plugin marketplaces group them into plugins:

| Plugin | Contents |
|---|---|
| `bitdrift-cli` | `bd-cli` and `bd-cuj` skills for operating bitdrift with the `bd` CLI |
| `bitdrift-sdk` | `bd-instrumentation` and `bd-docs` skills for adding the Capture SDK to your app |
| `bitdrift-mcp` | The hosted bitdrift MCP server (`https://mcp.bitdrift.ai/`); sign in when connecting |

## Install using npx [skills cli](https://skills.sh/)

```bash
npx skills add bitdriftlabs/bd-skills
```

### Updating skills

```bash
npx skills update --all
```

If you installed from an SSH or `.git` URL and `npx skills update` reports "Multiple current paths
match" for bitdrift skills, reinstall once with `npx skills add bitdriftlabs/bd-skills`, using the
same scope and skills you chose before. Later updates then work normally.

## Claude Code

```text
/plugin marketplace add bitdriftlabs/bd-skills
/plugin install bitdrift-cli@bitdrift
/plugin install bitdrift-sdk@bitdrift
/plugin install bitdrift-mcp@bitdrift
```

References: [Claude Code plugin docs](https://code.claude.com/docs/en/discover-plugins) · [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json)

## Codex

```bash
codex plugin marketplace add bitdriftlabs/bd-skills
codex plugin add bitdrift-cli@bitdrift
codex plugin add bitdrift-sdk@bitdrift
codex plugin add bitdrift-mcp@bitdrift
```

Reference: [.agents/plugins/marketplace.json](.agents/plugins/marketplace.json)

## GitHub Copilot

```bash
copilot plugin marketplace add bitdriftlabs/bd-skills
copilot plugin install bitdrift-cli@bitdrift
copilot plugin install bitdrift-sdk@bitdrift
copilot plugin install bitdrift-mcp@bitdrift
```

Reference: [Install plugins in Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-finding-installing)

## Dependencies

The skills themselves are markdown files. To use the bitdrift platform from an agent, you will also
need the [`bd` CLI](https://github.com/bitdriftlabs/bd-cli-releases/blob/main/README.md). Follow
its README for the current supported distribution methods.

To get started using the bitdrift platform, sign up [here](https://bitdrift.io/signup).

## License

See [LICENSE](LICENSE) for details.
