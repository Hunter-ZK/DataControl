[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
Write-Host "[DataControl] Model selection is now in the Intelligent Q&A chat window."
Write-Host "[DataControl] Open http://127.0.0.1:5173 -> 智能问数 -> 对话模型."
& (Join-Path $PSScriptRoot "start-dev.ps1")
