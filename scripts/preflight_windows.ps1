<#
.SYNOPSIS
  Integration-machine preflight for the Open Agent Hackathon build.
  Checks hardware, Docker Desktop, WSL2, resource allocation, port availability,
  and (once installed) Zetaris and Nightshift connectivity. Writes a report.

.USAGE
  Open PowerShell (not as admin unless Docker prompts for it) and run:
    Set-ExecutionPolicy -Scope Process Bypass
    .\preflight_windows.ps1
  Optional, once runtimes are running and you have credentials:
    .\preflight_windows.ps1 -ZetarisUrl http://localhost:8888/api/v1.0 -ZetarisOrgId 1 -ZetarisApiKey $env:ZETARIS_API_KEY `
                            -NightshiftUrl http://127.0.0.1:8088/v1 -NightshiftToken $env:METERLESS_RUNTIME_TOKEN

  The report is written to .\preflight_report.md. Secrets are never written to it.
  Nothing here installs, changes settings, or sends data anywhere except to the two local runtimes you name.
#>

[CmdletBinding()]
param(
  [string]$ZetarisUrl = "",
  [string]$ZetarisOrgId = "",
  [string]$ZetarisApiKey = "",
  [string]$NightshiftUrl = "",
  [string]$NightshiftToken = "",
  [string]$ReportPath = ".\preflight_report.md",
  [string]$PythonExecutable = "python"
)

$ErrorActionPreference = "Continue"
$results = New-Object System.Collections.Generic.List[object]
$projectRoot = Split-Path $PSScriptRoot -Parent

function Add-Check {
  param([string]$Area, [string]$Check, [string]$Status, [string]$Detail)
  foreach ($secret in @($ZetarisApiKey, $NightshiftToken)) {
    if ($secret) { $Detail = $Detail.Replace($secret, "...redacted") }
  }
  $Detail = $Detail -replace '(?i)Bearer\s+[^\s,;]+', '...redacted'
  $results.Add([pscustomobject]@{ Area = $Area; Check = $Check; Status = $Status; Detail = $Detail })
}

function Test-SelectOneBody {
  param([string]$Body)
  if (-not (Get-Command $PythonExecutable -ErrorAction SilentlyContinue)) { return $false }
  $validator = 'import json,sys; sys.path.insert(0,sys.argv[1]); from app.adapters.validation import validate_select_one; validate_select_one(json.loads(sys.stdin.read()))'
  $Body | & $PythonExecutable -c $validator $projectRoot 2>$null | Out-Null
  return ($LASTEXITCODE -eq 0)
}

# Thresholds from the Participant Setup Guide / Technical Execution Guide
$MinHostRamGB   = 16
$MinDockerRamGB = 8
$MinDockerCpus  = 4
$MinFreeDiskGB  = 15

Write-Host "== Hardware =="
$os  = Get-CimInstance Win32_OperatingSystem
$cs  = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$ramGB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
$logicalCpus = ($cpu | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum
Add-Check "Hardware" "Windows version" "INFO" "$($os.Caption) build $($os.BuildNumber)"
Add-Check "Hardware" "Host RAM >= ${MinHostRamGB} GB" ($(if ($ramGB -ge $MinHostRamGB) {"PASS"} else {"FAIL"})) "$ramGB GB installed"
Add-Check "Hardware" "Logical CPUs" ($(if ($logicalCpus -ge 8) {"PASS"} elseif ($logicalCpus -ge $MinDockerCpus) {"WARN"} else {"FAIL"})) "$logicalCpus logical processors ($($cpu.Name.Trim()))"

# Disk: system drive plus whatever drive holds Docker's WSL data (default C:)
foreach ($drive in Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Free -ne $null }) {
  $freeGB = [math]::Round($drive.Free / 1GB, 1)
  $st = if ($freeGB -ge $MinFreeDiskGB) {"PASS"} else {"WARN"}
  Add-Check "Hardware" "Free disk on $($drive.Name):" $st "$freeGB GB free (need >= ${MinFreeDiskGB} GB on the drive hosting Docker/WSL data)"
}

Write-Host "== Virtualization =="
try {
  $hv = (Get-CimInstance Win32_ComputerSystem).HypervisorPresent
  Add-Check "Virtualization" "Hypervisor present" ($(if ($hv) {"PASS"} else {"FAIL"})) "HypervisorPresent=$hv (needed for WSL2/Docker Desktop)"
} catch { Add-Check "Virtualization" "Hypervisor present" "UNKNOWN" $_.Exception.Message }

Write-Host "== WSL2 =="
$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if ($wsl) {
  # wsl.exe writes UTF-16LE, which arrives with NUL between characters; strip them before matching
  $wslStatus = (& wsl.exe --status 2>&1 | Out-String) -replace "`0", ""
  $defaultV2 = $wslStatus -match "Default Version:\s*2"
  Add-Check "WSL2" "wsl.exe present" "PASS" "found"
  Add-Check "WSL2" "Default WSL version is 2" ($(if ($defaultV2) {"PASS"} else {"WARN"})) ($wslStatus.Trim() -replace "`r?`n", " | ")
  $distros = (& wsl.exe -l -v 2>&1 | Out-String) -replace "`0", ""
  Add-Check "WSL2" "Distributions" "INFO" ($distros.Trim() -replace "`r?`n", " | ")
  $hasDockerDistro = $distros -match "docker-desktop"
  Add-Check "WSL2" "docker-desktop WSL distro registered" ($(if ($hasDockerDistro) {"PASS"} else {"WARN"})) ($(if ($hasDockerDistro) {"present"} else {"not found; Docker Desktop may not be using the WSL2 backend"}))
} else {
  Add-Check "WSL2" "wsl.exe present" "FAIL" "WSL not installed. Run 'wsl --install' from an elevated PowerShell, reboot, then re-run this script."
}

# .wslconfig governs RAM/CPU for the WSL2 VM that Docker Desktop uses
$wslconfig = Join-Path $env:USERPROFILE ".wslconfig"
if (Test-Path $wslconfig) {
  $cfg = Get-Content $wslconfig -Raw
  $memLine = ($cfg | Select-String -Pattern "memory\s*=\s*(\S+)" -AllMatches).Matches | Select-Object -First 1
  $cpuLine = ($cfg | Select-String -Pattern "processors\s*=\s*(\d+)" -AllMatches).Matches | Select-Object -First 1
  Add-Check "WSL2" ".wslconfig memory" "INFO" ($(if ($memLine) {$memLine.Groups[1].Value} else {"not set (WSL defaults to ~50% of host RAM, capped at 8 GB on some builds)"}))
  Add-Check "WSL2" ".wslconfig processors" "INFO" ($(if ($cpuLine) {$cpuLine.Groups[1].Value} else {"not set (defaults to all host logical CPUs)"}))
} else {
  Add-Check "WSL2" ".wslconfig present" "INFO" "none; WSL2 uses defaults. If Docker reports < ${MinDockerRamGB} GB below, create %USERPROFILE%\.wslconfig with [wsl2] memory=${MinDockerRamGB}GB processors=${MinDockerCpus} then 'wsl --shutdown'."
}

Write-Host "== Docker Desktop =="
$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
  $ver = (& docker version --format '{{.Server.Version}}' 2>&1 | Out-String).Trim()
  if ($LASTEXITCODE -eq 0 -and $ver -notmatch "error|cannot connect") {
    Add-Check "Docker" "Docker engine reachable" "PASS" "server $ver"
    $info = (& docker info --format '{{json .}}' 2>$null | Out-String)
    try {
      $j = $info | ConvertFrom-Json
      $dockerRamGB = [math]::Round($j.MemTotal / 1GB, 1)
      $dockerCpus  = [int]$j.NCPU
      Add-Check "Docker" "RAM available to Docker >= ${MinDockerRamGB} GB" ($(if ($dockerRamGB -ge $MinDockerRamGB) {"PASS"} else {"FAIL"})) "$dockerRamGB GB"
      Add-Check "Docker" "CPUs available to Docker >= ${MinDockerCpus}" ($(if ($dockerCpus -ge $MinDockerCpus) {"PASS"} else {"FAIL"})) "$dockerCpus"
      Add-Check "Docker" "Backend" "INFO" "OS=$($j.OperatingSystem); Driver=$($j.Driver); DockerRootDir=$($j.DockerRootDir)"
    } catch { Add-Check "Docker" "docker info parse" "WARN" "could not parse docker info JSON" }
    $compose = (& docker compose version 2>&1 | Out-String).Trim()
    Add-Check "Docker" "docker compose" ($(if ($LASTEXITCODE -eq 0) {"PASS"} else {"WARN"})) $compose
  } else {
    Add-Check "Docker" "Docker engine reachable" "FAIL" "docker CLI found but engine not responding. Start Docker Desktop and re-run. Raw: $ver"
  }
} else {
  Add-Check "Docker" "docker CLI present" "FAIL" "Docker Desktop not installed or not on PATH."
}

Write-Host "== Ports =="
# Zetaris REST 8888 (8889 internal), Nightshift runtime 8088 (guide example), Streamlit 8501
foreach ($p in 8888, 8889, 8088, 8501) {
  $conn = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if ($conn) {
    $procId = ($conn | Select-Object -First 1).OwningProcess
    $pname = (Get-Process -Id $procId -ErrorAction SilentlyContinue).ProcessName
    Add-Check "Ports" "Port $p" "INFO" "LISTENING (pid $procId $pname). Expected if the matching runtime is already running; a conflict otherwise."
  } else {
    Add-Check "Ports" "Port $p" "INFO" "free"
  }
}

Write-Host "== Toolchain =="
foreach ($tool in @(@("python","--version"), @("py","--version"), @("node","--version"), @("npm","--version"), @("git","--version"), @("cursor","--version"))) {
  $cmd = Get-Command $tool[0] -ErrorAction SilentlyContinue
  if ($cmd) {
    $v = (& $tool[0] $tool[1] 2>&1 | Out-String).Trim()
    Add-Check "Toolchain" $tool[0] "PASS" $v
  } else {
    Add-Check "Toolchain" $tool[0] ($(if ($tool[0] -in @("py","cursor")) {"INFO"} else {"WARN"})) "not on PATH"
  }
}

Write-Host "== Zetaris connectivity (optional) =="
if ($ZetarisUrl) {
  $base = $ZetarisUrl.TrimEnd('/')
  try {
    $r = Invoke-WebRequest -Uri $base -Method GET -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    Add-Check "Zetaris" "Base URL reachable" "PASS" "HTTP $($r.StatusCode) from $base"
  } catch {
    $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "no response" }
    Add-Check "Zetaris" "Base URL reachable" ($(if ($code -is [int]) {"PASS"} else {"FAIL"})) "HTTP $code from $base (a 401/404 still proves the server is up)"
  }
  if ($ZetarisApiKey -and $ZetarisOrgId) {
    $headers = @{ Authorization = "Bearer $ZetarisApiKey"; "X-Org-ID" = $ZetarisOrgId; "X-Request-ID" = [guid]::NewGuid().ToString(); "Content-Type" = "application/json" }
    $body = @{ queryId = [guid]::NewGuid().ToString(); sql = "SELECT 1 AS one"; source = "SqlEditor"; limit = 1 } | ConvertTo-Json
    try {
      $r = Invoke-WebRequest -Uri "$base/sql-editor/sqls/run" -Method POST -Headers $headers -Body $body -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
      if (Test-SelectOneBody $r.Content) {
        Add-Check "Zetaris" "SELECT 1 via REST" "PASS" "Validated exactly one cell with value 1; HTTP $($r.StatusCode)."
      } else {
        Add-Check "Zetaris" "SELECT 1 via REST" "FAIL" "SQL result validation failed. Check the installed response mapping and configured Python environment. HTTP success alone is insufficient."
      }
    } catch {
      Add-Check "Zetaris" "SELECT 1 via REST" "FAIL" "$($_.Exception.Message). Check the installed API reference: body field names (queryId/sql/source/limit) follow the installed schema."
    }
  } else {
    Add-Check "Zetaris" "SELECT 1 via REST" "SKIP" "no API key/org ID supplied"
  }
} else { Add-Check "Zetaris" "connectivity" "SKIP" "no -ZetarisUrl supplied; re-run after install" }

Write-Host "== Nightshift connectivity (optional) =="
if ($NightshiftUrl) {
  $nbase = ($NightshiftUrl.TrimEnd('/')) -replace '(/v1)+$', '/v1'
  if ($NightshiftToken) {
    $h = @{ Authorization = "Bearer $NightshiftToken"; "meterless-app" = "llm-cost-intelligence-preflight"; "meterless-scope" = "user" }
    try {
      $r = Invoke-WebRequest -Uri "$nbase/models" -Method GET -Headers $h -TimeoutSec 20 -UseBasicParsing -ErrorAction Stop
      if (-not (Get-Command $PythonExecutable -ErrorAction SilentlyContinue)) { throw "Configured Python executable is unavailable." }
      $validator = 'import json,sys; sys.path.insert(0,sys.argv[1]); from app.adapters.validation import parse_model_discovery; print(json.dumps(parse_model_discovery(json.loads(sys.stdin.read()))))'
      $validated = $r.Content | & $PythonExecutable -c $validator $projectRoot 2>$null
      if ($LASTEXITCODE -ne 0) { throw "Model discovery validation failed; check response structure and configured Python environment." }
      $models = @($validated | ConvertFrom-Json)
      $nemo = $models | Where-Object { $_ -match "nemotron" }
      Add-Check "Nightshift" "GET /v1/models" "PASS" "$($models.Count) routes: $($models -join ', ')"
      Add-Check "Nightshift" "Nemotron route visible (discovery only)" ($(if ($nemo) {"PASS"} else {"WARN"})) ($(if ($nemo) {($nemo -join ', ') + "; working-feature identity remains unverified"} else {"none; configure NVIDIA in Providers and a Nemotron lane. meterless/auto is not a Nemotron ID."}))
    } catch {
      Add-Check "Nightshift" "GET /v1/models" "FAIL" "$($_.Exception.Message) at $nbase (is the desktop runtime running? token from Console?)"
    }
  } else { Add-Check "Nightshift" "GET /v1/models" "SKIP" "no runtime token supplied" }
} else { Add-Check "Nightshift" "connectivity" "SKIP" "no -NightshiftUrl supplied; re-run after install" }

# Report
$fails = ($results | Where-Object Status -eq "FAIL").Count
$warns = ($results | Where-Object Status -eq "WARN").Count
$skips = ($results | Where-Object Status -eq "SKIP").Count
$unknowns = ($results | Where-Object Status -eq "UNKNOWN").Count
$verdict = if ($fails -gt 0) { "NOT READY" } elseif ($skips -gt 0 -or $unknowns -gt 0) { "INCOMPLETE" } elseif ($warns -gt 0) { "PREFLIGHT CHECKS PASS WITH WARNINGS" } else { "PREFLIGHT CHECKS PASS" }

$md = @()
$md += "# Integration machine preflight"
$md += ""
$md += "Machine: $env:COMPUTERNAME | Run: $(Get-Date -Format 'yyyy-MM-dd HH:mm zzz') | Verdict: **$verdict** ($fails FAIL, $warns WARN, $skips SKIP, $unknowns UNKNOWN)"
$md += "Machine/connectivity checks only. End-to-end sponsor readiness remains unverified; use the Python smoke diagnostic for request evidence."
$md += ""
$md += "| Area | Check | Status | Detail |"
$md += "|---|---|---|---|"
foreach ($r in $results) { $md += "| $($r.Area) | $($r.Check) | $($r.Status) | $(($r.Detail -replace '\|','\|'))|" }
$md += ""
$md += "Thresholds: host RAM >= ${MinHostRamGB} GB, Docker RAM >= ${MinDockerRamGB} GB, Docker CPUs >= ${MinDockerCpus}, free disk >= ${MinFreeDiskGB} GB (Participant Setup Guide / Technical Execution Guide §4)."
$md += "No secrets are recorded in this report."
$md -join "`n" | Set-Content -Path $ReportPath -Encoding UTF8

$results | Format-Table -AutoSize -Wrap
Write-Host ""
Write-Host "Verdict: $verdict  ->  report written to $ReportPath"
if ($fails -gt 0 -or $skips -gt 0 -or $unknowns -gt 0) { exit 1 }
exit 0
