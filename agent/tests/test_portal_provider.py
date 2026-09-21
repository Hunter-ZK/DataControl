import httpx
from agent3.contracts.authz import AuthzContext
from agent3.metadata.datacontrol_http import PortalMetadataProvider
from agent3.semantic.datacontrol import load_portal_semantics
from agent3.services.core import Agent3Core

def handler(request:httpx.Request):
    path=request.url.path
    if path.endswith('/tables/DS000001'):
        return httpx.Response(200,json={"code":"OK","data":{"assetId":"DS000001","tableName":"dw.dwd_loan_snapshot","bizName":"贷款余额快照","bizDefinition":"贷款余额日快照","rowCount":10,"columns":[{"columnName":"dt","dataType":"string","cnName":"数据日期"},{"columnName":"region_code","dataType":"string","cnName":"地区"},{"columnName":"balance_amt","dataType":"decimal(20,2)","cnName":"贷款余额"}]}})
    if path.endswith('/tables'):
        return httpx.Response(200,json={"code":"OK","data":[{"assetId":"DS000001","tableName":"dw.dwd_loan_snapshot","bizName":"贷款余额快照"}]})
    if path.endswith('/metrics'):
        return httpx.Response(200,json={"code":"OK","data":[{"metricCode":"loan_balance","name":"贷款余额","aliases":"余额","sourceDatasetId":"DS000001","aggregation":"sum","measureColumn":"balance_amt","timeAdditivity":"non_additive","caliber":"期末余额"}]})
    return httpx.Response(404)

def test_portal_is_read_only_fact_source_for_agent_core():
    client=httpx.Client(transport=httpx.MockTransport(handler));provider=PortalMetadataProvider('http://portal/api/v1',client=client);table=provider.get_table(AuthzContext.system(),"dw.dwd_loan_snapshot");assert table and table.column('balance_amt')
    semantics=load_portal_semantics('http://portal/api/v1',provider,client=client);core=Agent3Core(metadata=provider,semantics=semantics);assert core.resolve_metric(AuthzContext.system(),"余额")["resolved"] is True
