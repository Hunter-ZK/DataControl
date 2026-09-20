# 06 · Synthetic validation data

`samples/generate_demo_data.py` deterministically creates a rich, non-sensitive dataset:

- 8 business domains
- 180 datasets across ODS/DWD/DWS/ADS/DIM
- 2,401 generated fields in the current seed
- ONLINE / DEPRECATED / OFFLINE states
- common and long-tail assets
- owners, departments, update frequencies, schedule descriptions, volumes and row counts
- table lineage chains with confirmed/inferred edges
- 12 business metrics
- multiple code tables and code values
- 2,593 search documents for datasets, fields and metrics

The generator uses a fixed seed so screenshots and test expectations remain reproducible.
