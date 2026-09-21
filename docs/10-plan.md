# 10 · Delivery plan

## P0 — foundation
Repository, backend skeleton, synthetic assets, search spike, cross-platform scripts and CI. **Complete.**

## P1 — asset backend
Asset/reference/application models, read APIs, local auth boundary, migrations and rich synthetic fixtures. **Complete.**

## P2 — product portal
Formal Vue 3 + TypeScript product UI, routed asset pages, responsive shell and cross-platform frontend quality gate. **Complete / frozen on main.**

## P3 — intelligence and relations
P3 implementation is complete as a release candidate on `feature/p3-intelligence-relations`; real-model/user acceptance remains before merge.

### P3-A · Search and relationship intelligence — complete
- unified asset index across datasets, fields and reference assets;
- suggestions, facets and highlighting;
- multi-level upstream/downstream graph;
- directed path finder;
- downstream impact analysis;
- routed relationship workspace and dataset-detail navigation.

### P3-B · Embedded DataAgent migration — complete
- pinned `Hunter-ZK/DataAgent-dsh@f04e266c6fe93e6e89d7e4b5c6e31128082a8c96` migration baseline;
- Agent3 Core/adapters, dsh assets, Skills, Guard and semantic assets live in `DataControl/agent`;
- Portal and Agent remain separate process/runtime boundaries inside one monorepo;
- Portal and DataAgent share one repository-local Python environment with supported range `>=3.13,<3.15`;
- Windows/macOS/Linux setup/start/verify and CI do not clone another repository;
- Agent architecture/security gates are preserved.

### P3-C · Intelligent Q&A product integration — implementation complete
- local Embedded Agent Gateway on port 8910;
- dsh `dataagent-headless` session bridge using the actual Harness headless JSON event contract;
- resumable session identity;
- dsh Agent Loop -> Agent3 MCP -> Agent3 Core -> Portal read-only facts;
- trusted SQL generation/validation and evidence presentation;
- Agent3 MCP tool activity projected to the UI;
- hidden reasoning discarded at the Gateway;
- no production SQL execution;
- real-model E2E acceptance script with destructive-request safety check.

### P3 release gate — pending local/user acceptance only
1. set a user-owned `DEEPSEEK_API_KEY` before `start-dev`;
2. run `scripts/p3_agent_acceptance.py` against the running product;
3. verify the resulting `.local/p3-agent-acceptance.json` and UI status;
4. complete product acceptance;
5. merge PR #4 only after explicit user approval.

No ACP contract is used. P3 is built against DeepSeek Harness's headless task surface and Agent3's streamable-HTTP MCP adapter.

## P4 — production hardening
Enterprise SSO/LDAP, production MySQL deployment, permissions/security hardening, audit/observability, caching, operational deployment and performance gates.
