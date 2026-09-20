# 05 · Agent integration V3

Runtime contract stays: FastAPI -> ACP stdio -> dsh -> MCP -> Agent3 -> Portal internal API.

Model choice is configuration, not portal business logic:
- development: DeepSeek API or Qwen API
- future: internal OpenAI-compatible endpoint

P0 does not claim external dsh validation unless the locked runtime, Agent3 source and model credentials are present. P3 is the complete production integration phase. No SQL execution is permitted.
