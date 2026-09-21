$ErrorActionPreference="Stop";$agentRoot=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path;$repoRoot=(Resolve-Path (Join-Path $agentRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($env:DSH_HOME)) { $env:DSH_HOME=Join-Path $repoRoot ".local\dsh-home" };$env:DSH_TELEMETRY_MODE="DISABLED"
$dsh=Join-Path $agentRoot "dsh\node_modules\.bin\dsh.cmd";if(-not(Test-Path $dsh)){throw "Run .\scripts\setup-agent.ps1 first"};if([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)){Write-Warning "DEEPSEEK_API_KEY is not set"}
Push-Location $repoRoot;try{& $dsh --profile dataagent --no-open;exit $LASTEXITCODE}finally{Pop-Location}
