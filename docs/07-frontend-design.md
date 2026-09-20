# 07 · Frontend design baseline

The supplied 9-screen prototype remains the information-architecture reference. P0 raises the visual baseline rather than pixel-copying it.

## Principles
- Search is the primary hero action.
- Reduce card-wall effect: use whitespace, typography and separators before borders.
- Dataset detail must answer in 3 seconds: what it is, whether usable, owner, freshness, where to trace/ask.
- Technical identifiers use monospace treatment.
- ODS/DWD/DWS/ADS/DIM preserve stable layer colors.
- Dense pages use progressive disclosure and inspector panels.
- Agent UI exposes activity/tool summaries, not private reasoning.

## P0 prototype
`web/prototype/index.html` includes two switchable reference pages: dashboard and dataset detail, backed by the synthetic dataset APIs when the backend is running.
