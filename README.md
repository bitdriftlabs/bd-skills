# bitdrift Agent Skills

Agent skills for [bitdrift](https://bitdrift.ai) — mobile observability that stores telemetry on-device and uploads only what you need.

- **bd-cli** — CLI usage: workflows, charts, sessions, issues, admin
- **bd-docs** — Fetch and search bitdrift documentation

## Installation

Use your preferred skills distribution channel to install these skills.

## npx skills

```bash
npx skills add bitdriftlabs/bd-skills
```

Reference: [skills.sh](https://skills.sh/)

## GitHub Copilot

```bash
copilot plugin marketplace add bitdriftlabs/bd-skills
copilot plugin install bd@bd-skills
```

Reference: [Install plugins in Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-finding-installing)

## Claude Code

```text
/plugin marketplace add bitdriftlabs/bd-skills
/plugin install bd@bd-skills
```

References: [Claude Code plugin docs](https://code.claude.com/docs/en/discover-plugins) · [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json)

## Dependencies

The skills themselves are markdown files. To use the bitdrift platform from an agent, you will also
need the [`bd` CLI](https://docs.bitdrift.io/cli/quickstart.html).

To get started using the bitdrift platform, sign up [here](https://bitdrift.io/signup).

## License

See [LICENSE](LICENSE) for details.
