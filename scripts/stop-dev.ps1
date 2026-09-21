[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
$targets=@(
  @{ Port=8000; Marker="backend.app.main:app"; Name="DataControl API" },
  @{ Port=8900; Marker="agent3.adapters.mcp.server"; Name="Agent3 MCP" },
  @{ Port=8910; Marker="dataagent_gateway.app:app"; Name="DataAgent Gateway" }
)

foreach($target in $targets){
  $connections=@(Get-NetTCPConnection -LocalPort $target.Port -State Listen -ErrorAction SilentlyContinue)
  if($connections.Count -eq 0){
    Write-Host "$($target.Name): no listener on $($target.Port)"
    continue
  }
  foreach($pidValue in ($connections | Select-Object -ExpandProperty OwningProcess -Unique)){
    $process=Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
    $commandLine=[string]$process.CommandLine
    if($commandLine -notlike "*$($target.Marker)*"){
      throw "$($target.Name) port $($target.Port) is owned by PID $pidValue, but its command line does not match DataControl marker '$($target.Marker)'. Refusing to kill an unrelated process."
    }
    Stop-Process -Id $pidValue -Force -ErrorAction Stop
    Write-Host "$($target.Name): stopped stale DataControl process PID $pidValue on port $($target.Port)"
  }
}
