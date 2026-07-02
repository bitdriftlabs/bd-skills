# bitdrift Agent Skills

Agent skills for [bitdrift](https://bitdrift.ai) — mobile observability that stores telemetry on-device and uploads only what you need.

- **bd-cli** — CLI usage: workflows, charts, sessions, issues, admin
- **bd-instrumentation** - Installing and configuring the SDK to instrument iOS, Android, or React Native apps
- **bd-docs** — Fetch and search bitdrift documentation
- **bd-issue-match** — Writing BDRL scripts for issue/crash upload matching: filter noise, chart crash characteristics

## Installation

Use your preferred skills distribution channel to install these skills.

## Install using npx [skills cli](https://skills.sh/)

```bash
npx skills add bitdriftlabs/bd-skills
```

### Updating skills

```bash
npx skills update --all
```

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
