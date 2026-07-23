---
name: bd-cuj
description: "Set up Critical User Journey (CUJ) monitoring in bitdrift. Deploys a complete observability stack: path discovery (sankey), conversion funnel, completion rate SLO, key step duration alerting, session capture, and a two-tab dashboard. Trigger when a user wants to monitor a journey end-to-end, track conversion and drop-off, measure step duration, or set up SLOs on a business-critical flow such as checkout, onboarding, login, or search."
---

# Critical User Journey (CUJ) Monitoring

> For CLI usage, workflow creation, and alert syntax, see $bd-cli.
> For SDK integration and instrumentation, see $bd-instrumentation.

This skill is a guided, interactive setup. Work through phases in order, loading reference files on demand as each phase begins.

## Core rules

- **Never guess field names, event names, or matcher values.** The user supplies all identifiers in Phase 0. Do not infer them from code or prior context.
- **Do not deploy anything until the user has approved the Phase 0 discovery summary.**
- **Gate between every phase.** After each phase: report the created resource ID(s) (workflow/alert/dashboard) and link(s) where applicable, then ask "Ready to continue to [next phase]?" before loading the next reference file.

## Phases

| # | Phase | Output | Reference |
|---|---|---|---|
| 0 | Discovery | Approved event map, key step, scope, app IDs, network paths | [references/discovery.md](references/discovery.md) |
| 1 | Sankey | Path discovery workflow | [references/sankey.md](references/sankey.md) |
| 2 | Funnel | Funnel workflow (funnel + key step timing + slow session capture) + separate completion rate workflow (for SLOs) | [references/funnel.md](references/funnel.md) |
| 3 | Network | Network RED workflow | [references/network.md](references/network.md) |
| 4 | Alerts | Completion rate MWMBR SLO + key step p95 alert | [references/alerts.md](references/alerts.md) |
| 5 | Dashboard | Two-tab dashboard: Journey + Network | [references/dashboard.md](references/dashboard.md) |

Start with [references/discovery.md](references/discovery.md).
