# Shared Windows startup guard for versioned DeepSeek Harness profile overlays.
# A package.json or setup marker alone is insufficient: old YAML can survive an upgrade.
function Test-DataAgentProfilesCurrent {
  param([Parameter(Mandatory=$true)][string]$RepoRoot)

  $home = Join-Path $RepoRoot ".local\dsh-home-v0.2.1-rc.3\profiles"
  $checks = @(
    @{ Source="agent\dsh\profile\headless.patch.yml"; Active="dataagent-headless\cordis.patch.yml" },
    @{ Source="agent\dsh\profile\cordis.patch.yml"; Active="dataagent\cordis.patch.yml" }
  )
  foreach ($check in $checks) {
    $source = Join-Path $RepoRoot $check.Source
    $profile = Join-Path $home $check.Active
    $package = Join-Path (Split-Path -Parent $profile) "package.json"
    if (-not ((Test-Path -LiteralPath $source) -and (Test-Path -LiteralPath $profile) -and (Test-Path -LiteralPath $package))) {
      return $false
    }
    try {
      $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
      $profileHash = (Get-FileHash -LiteralPath $profile -Algorithm SHA256).Hash
      if ($sourceHash -ne $profileHash) { return $false }
    } catch {
      return $false
    }
  }
  return $true
}
