# task-planning

## Trigger
Multi-step warehouse development and cross-asset tasks when a single governed SQL question is insufficient. Use only in the multi-step profile.

## Steps and tools
1. Before invoking development tools, present a short **visible task plan** with 2–5 user-centered steps. Each step names its output, its known evidence and any user decision required. Do not expose hidden chain-of-thought.
2. Establish source data set, data grain, existing target fields and transformation scope through approved Agent3 MCP calls. Prefer downstream DWD/DWS/ADS assets; do not assume raw ODS is the query source.
3. Work one stage at a time: confirm metadata → propose SQL / draft → static validation → summarize dependencies and open questions.
4. Never invent a JOIN or business relationship. If source-to-target mapping is unknown, stop and ask for it.
5. Date partition or business-period conditions use user-controlled MaxCompute/DataWorks scheduling parameters such as `'${dt}'` when a field is governed; do not use `MAX_PT` or infer the “latest” physical partition.
6. Describe each completed stage only if the actual tool result exists. Never claim that an intended step was executed.
7. Ask for explicit confirmation before generating high-impact SQL drafts. This is confirmation to **generate**, not authorization to execute.

## Output
**任务目标** → **步骤清单（待处理 / 已完成 / 需确认）** → **每阶段产物** → **风险与下一步**.
The DataControl UI can show tool-derived stage progress separately; avoid pretending the UI's predefined stages are the model's private plan.

## Good / bad
Good: “先核实 DWS 目标表的字段和粒度，再生成单源映射 SQL，最后列出测试规则。”
Bad: “已部署分区覆盖任务。” The system has no deployment capability.

## Forbidden
No production execution, arbitrary shell/filesystem/network tools, fictitious plans or synthetic tool results.
