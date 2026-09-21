from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'web'
python_steps=[[sys.executable,'-m','alembic','upgrade','head'],[sys.executable,'samples/generate_demo_data.py'],[sys.executable,'samples/enrich_p1_data.py'],[sys.executable,'samples/rebuild_search_index.py'],[sys.executable,'-m','ruff','check','.'],[sys.executable,'-m','pytest','-q'],[sys.executable,'scripts/search_benchmark.py']]
for cmd in python_steps: print('>',' '.join(map(str,cmd)));subprocess.run(cmd,cwd=ROOT,check=True)
npm=shutil.which('npm')
if npm is None: raise SystemExit('npm is required for verification')
for args in ([npm,'run','type-check'],[npm,'run','test'],[npm,'run','build']): print('>',' '.join(args));subprocess.run(args,cwd=WEB,check=True)
agent_py=ROOT/'.venv-agent'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if agent_py.exists():
    for args in ([str(agent_py),'agent/scripts/check_architecture.py'],[str(agent_py),'-m','pytest','-q','agent/tests']): print('>',' '.join(args));subprocess.run(args,cwd=ROOT,check=True)
    guard=ROOT/'agent/guard-plugin'
    subprocess.run([npm,'run','build'],cwd=guard,check=True);subprocess.run([npm,'test'],cwd=guard,check=True)
else:
    print('! Agent verification skipped: .venv-agent is missing. Run scripts/setup-agent.sh or setup-agent.ps1 for the Python 3.14 Agent gate.')
print('\nP3 MONOREPO VERIFICATION PASSED (Agent gate runs when .venv-agent is installed)')
