# DataControl documentation · V3

This directory is the P0 development baseline after the project moved from Java/Spring to Python/FastAPI.

## Current product boundary
DataControl is a **read-only data asset service portal**. Its four product pillars are:
1. asset browsing and unified asset views;
2. asset search;
3. relationship / lineage tracing;
4. intelligent Q&A through dsh + Agent3.

The platform does **not** currently build DataWorks/MaxCompute ingestion, asset-entry UI, governance/approval workflows, SQL execution, or production-data preview.

## Approved changes from the V2 source material
- Java/Spring/MyBatis/Lucene stack replaced by Python/FastAPI/SQLAlchemy and an embedded search abstraction.
- standalone scheduling calendar removed; schedule/operation metadata moves into dataset detail.
- stable `asset_id` becomes the persistent identity; table/field names are mutable technical identifiers.
- development model provider may be DeepSeek or Qwen; future internal model is a provider configuration, not a portal rewrite.
- model chain-of-thought is never exposed; UI shows activity/tool summaries only.
- existing 9-screen prototype is an information-architecture and visual-direction reference, not a pixel-perfect implementation target.

## P0 documents
- `00-project-scope.md`: scope and exclusions
- `01-architecture.md`: system architecture and frozen boundaries
- `02-product-requirements.md`: V3 product requirements baseline
- `03-data-model.md`: stable identity and P0 domain model
- `04-api-contract.md`: P0 public API contract
- `05-agent-integration.md`: dsh/Agent3 boundary
- `06-demo-data.md`: synthetic validation datasets
- `07-frontend-design.md`: UI/design-system direction
- `08-security.md`: security boundary
- `09-development-standards.md`: coding rules
- `10-plan.md`: P0–P4 plan
- `11-acceptance.md`: P0 verification
- `12-environment.md`: local environment

P1 will expand the P0 data/API documents into the complete backend contract before full portal UI work starts.
