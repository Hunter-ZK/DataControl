# Agent boundary (P0)

The production direction remains **dsh runtime + Agent3 MCP tools**. Portal and Agent3 are both Python but stay isolated by an internal HTTP contract.

P0 intentionally does not vendor the user's existing Agent3 repository yet. Integration contract:

`Portal UI -> FastAPI chat service -> ACP stdio -> dsh -> MCP HTTP -> Agent3 -> Portal internal API`

Model provider is configuration (`deepseek`, `qwen`, later an internal OpenAI-compatible endpoint). The portal never calls a model SDK directly.

Real dsh/Agent3 end-to-end smoke verification is environment-gated because it requires the locked dsh package, Agent3 source and a configured model key. P0 code must not fake a successful external-model integration.
