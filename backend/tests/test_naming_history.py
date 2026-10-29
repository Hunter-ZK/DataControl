import uuid
from fastapi.testclient import TestClient
from backend.app.main import app

client=TestClient(app)
def auth(name:str,passwd:str):
    response=client.post("/api/v1/auth/login",json={"username":name,"password":passwd})
    assert response.status_code==200
    return {"Authorization":"Bearer "+response.json()["data"]["accessToken"]}

def test_run_history_is_user_owned_and_downloadable():
    first=auth("demo","DataControl123!")
    other=auth("admin","DataControlAdmin123!")
    payload={"title":"规范复核测试 "+str(uuid.uuid4())[:8],"payload":{
        "originalHeaders":["中文名"],
        "entries":[{"cnName":"贷款余额","suggestedName":"loan_bal","status":"已确认"}],
        "rootSuggestions":[],
    }}
    created=client.post("/api/v1/workbench/naming/runs",headers=first,json=payload)
    assert created.status_code==200
    run_id=created.json()["data"]["id"]
    assert any(x["id"]==run_id for x in client.get("/api/v1/workbench/naming/runs",headers=first).json()["data"])
    assert client.get(f"/api/v1/workbench/naming/runs/{run_id}/download",headers=other).status_code==404
    saved=client.get(f"/api/v1/workbench/naming/runs/{run_id}/download",headers=first)
    assert saved.status_code==200
    assert saved.content[:2]==b"PK"
    assert client.delete(f"/api/v1/workbench/naming/runs/{run_id}",headers=first).status_code==200
    assert client.get(f"/api/v1/workbench/naming/runs/{run_id}/download",headers=first).status_code==404
