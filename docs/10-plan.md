# 10 · Delivery plan

## P0 — foundation
Repository, backend skeleton, synthetic assets, search spike, cross-platform scripts and CI.

## P1 — asset backend
Asset/reference/application models, read APIs, local auth boundary, migrations and rich synthetic fixtures.

## P2 — product portal
Formal Vue 3 + TypeScript product UI, routed asset pages, responsive shell and cross-platform frontend quality gate.

## P3 — intelligence and relations
P3 is split into three coordinated tracks:

### P3-A · Search and relationship intelligence
- unified asset index;
- suggestions/facets/highlights;
- multi-level upstream/downstream graph;
- path finder;
- downstream impact analysis.

### P3-B · Embedded DataAgent migration
- pin `Hunter-ZK/DataAgent-dsh` source baseline;
- migrate required Agent3 Core/adapters, dsh profile/preset, Skills, guard and semantic assets into `DataControl/agent`;
- keep Portal and Agent as separate runtime boundaries inside one monorepo;
- reconcile Portal Python 3.13 with DataAgent's declared Python 3.14 baseline explicitly;
- extend Windows/macOS setup/start/verify scripts without cloning another repository;
- preserve DataAgent architecture/security gates.

### P3-C · Intelligent Q&A product integration
- Portal Agent Gateway to local embedded Agent service;
- dsh Agent Loop -> MCP -> Agent3 Core;
- trusted SQL generation/validation and evidence presentation;
- no production SQL execution;
- no hidden reasoning display;
- real end-to-end model/MCP acceptance before enabling the Agent readiness flag.

P3 must not assume ACP or any other Harness protocol that is not present in the migrated DataAgent implementation.

## P4 — production hardening
Enterprise SSO/LDAP, production MySQL deployment, permissions/security hardening, audit/observability, caching, operational deployment and performance gates.
