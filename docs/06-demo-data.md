# 06 · Synthetic validation data

P0 provides two deterministic, non-sensitive generators.

## Fast demo seed
`samples/generate_demo_data.py`
- 8 business domains
- 180 datasets across ODS/DWD/DWS/ADS/DIM
- about 2,400 fields
- ONLINE / DEPRECATED / OFFLINE states
- owners, departments, update frequencies, schedule descriptions, volumes and row counts
- confirmed/inferred table lineage
- 12 metrics and core code tables
- about 2,600 search documents

## Full-scale validation seed
`samples/generate_full_scale.py`
- exactly **1,361 datasets**, matching the current target asset scale
- **54,440 fields** (40 per dataset)
- 126 business metrics
- 40 code tables with hundreds of code values
- more than 1,000 table-lineage edges, including cross-domain links and inferred edges
- 55,000+ search documents covering datasets, fields, metrics and code tables
- common/long-tail assets, owners, departments, status variants, schedules, row counts and storage volumes

Both use a fixed random seed so screenshots, benchmarks and regression tests remain reproducible.
