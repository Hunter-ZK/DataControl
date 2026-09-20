# 00 · Project scope V3

DataControl is a read-only data asset service portal. V1 serves developers and business users through four pillars: **asset browsing, asset search, relationship tracing and intelligent Q&A**.

## In scope
- dashboard, asset catalog, unified dataset/column views
- standards/code tables, word roots, metrics/statistical definitions
- lineage/relationship explorer
- unified search
- dsh + Agent3 intelligent Q&A; generate/validate/explain SQL only
- USER/ADMIN portal operations and audit

## Out of scope
- DataWorks/MaxCompute ingestion and synchronization
- data governance workflow, approval/version publishing
- asset editing/import UI
- SQL execution, production-data preview/download
- standalone scheduling calendar (schedule is dataset detail metadata)

## Environment decisions
- Backend: Python/FastAPI, not Java/Spring.
- Development model: DeepSeek or Qwen API; future internal model via provider configuration.
- Rich synthetic data is the P0/P1 validation source.
