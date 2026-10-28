# etl-authoring
## Trigger
User requests a warehouse transformation, partition overwrite, or derived metric SQL.
## Method
1. Read all governed source datasets, target grain, and lineage.
2. Call generate_etl to produce a declarative draft using confirmed source columns.
3. Validate MaxCompute SQL; use the governed scheduling field with DataWorks parameter `'${dt}'` when applicable; include dependencies.
4. Identify scheduling, null, duplication and code-value conversion assumptions.
5. Prefer governed DWD/DWS/ADS assets and ask for missing transformation rules. Do not invent cross-table JOINs or assume ODS.
## Answer
Source/target map → dependencies → SQL draft → static validation → open questions.
## Examples
Good: An explicit partition key derived from a governed target.
Bad: Invent a business join between similarly named tables.
## Forbidden
Do not execute INSERT, overwrite any partition, or claim deployment.
