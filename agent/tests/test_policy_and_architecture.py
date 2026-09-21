import subprocess,sys
from pathlib import Path
import pytest
from agent3.contracts.authz import AuthzContext,DataScope
from agent3.policy.row_filter import PolicyError,RowFilterPolicy

def test_scope_rewrite_and_multitable_fail_closed():
    authz=AuthzContext(principal="u1",data_scopes=(DataScope("region_code",("440300",)),));rewritten,changed=RowFilterPolicy().apply(authz,"select balance_amt from dw.dwd_loan_snapshot");assert changed and "region_code = '440300'" in rewritten
    with pytest.raises(PolicyError): RowFilterPolicy().apply(authz,"select l.balance_amt from dw.dwd_loan_snapshot l join dw.dim_org o on l.org_id=o.org_id")
def test_architecture_boundary():
    root=Path(__file__).resolve().parents[1];result=subprocess.run([sys.executable,str(root/"scripts/check_architecture.py")],cwd=root,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
