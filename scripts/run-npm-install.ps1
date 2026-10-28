[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Name,
  [Parameter(Mandatory=$true)][string]$WorkingDirectory,
  [Parameter(Mandatory=$true)][string]$LogDirectory,
  [string]$CommandLine = "npm.cmd install --no-audit --no-fund --no-progress --maxsockets=5",
  [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = "Stop"
if ($TimeoutSeconds -lt 1) { throw "TimeoutSeconds must be positive." }
if (-not (Test-Path -LiteralPath $WorkingDirectory -PathType Container)) {
  throw "npm working directory not found: $WorkingDirectory"
}

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$stdout = Join-Path $LogDirectory "npm-$Name.stdout.log"
$stderr = Join-Path $LogDirectory "npm-$Name.stderr.log"
Remove-Item -LiteralPath $stdout,$stderr -Force -ErrorAction SilentlyContinue

# Use a native .NET Process rather than Start-Process -PassThru. The latter can
# expose an unset ExitCode on some Windows PowerShell hosts, producing the
# misleading "npm installation failed with exit code ." error.
$start = New-Object System.Diagnostics.ProcessStartInfo
$start.FileName = $env:ComSpec
if ([string]::IsNullOrWhiteSpace($start.FileName)) { $start.FileName = "cmd.exe" }
$start.WorkingDirectory = [System.IO.Path]::GetFullPath($WorkingDirectory)
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
# Let cmd redirect streams directly to files. This avoids pipe deadlocks and
# preserves complete diagnostics even for large npm installations.
$start.Arguments = '/d /s /c "' + $CommandLine + ' 1>"' + $stdout + '" 2>"' + $stderr + '""'

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $start
try {
  Write-Host "[DataControl] Installing $Name dependencies. Log: $stderr"
  if (-not $process.Start()) { throw "Could not launch npm for $Name." }
  $watch = [System.Diagnostics.Stopwatch]::StartNew()
  $nextNotice = 30000
  while (-not $process.WaitForExit(1000)) {
    if ($watch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
      & taskkill.exe /PID $process.Id /T /F 2>$null | Out-Null
      throw "$Name npm install timed out after $TimeoutSeconds seconds. See $stderr."
    }
    if ($watch.ElapsedMilliseconds -ge $nextNotice) {
      Write-Host "[DataControl] $Name npm is running; details in $stderr"
      $nextNotice += 30000
    }
  }
  $process.WaitForExit()
  $exitCode = [int]$process.ExitCode
  if ($exitCode -ne 0) {
    $outTail = if (Test-Path $stdout) { (Get-Content -LiteralPath $stdout -Tail 25) -join [Environment]::NewLine } else { "" }
    $errTail = if (Test-Path $stderr) { (Get-Content -LiteralPath $stderr -Tail 35) -join [Environment]::NewLine } else { "" }
    throw ("$Name npm installation failed with exit code $exitCode." +
      [Environment]::NewLine + "--- npm stdout ---" + [Environment]::NewLine +
      $outTail + [Environment]::NewLine + "--- npm stderr ---" +
      [Environment]::NewLine + $errTail)
  }
  Write-Host "[DataControl] $Name npm installation completed successfully."
} finally {
  $process.Dispose()
}
