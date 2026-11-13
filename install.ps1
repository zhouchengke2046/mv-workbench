$ErrorActionPreference = "Stop"
$Repo = $PSScriptRoot
$Target = Join-Path $HOME ".agents\skills\zz-mv-gongzuotai"
$Bin = Join-Path $HOME ".local\bin"

if ($args -contains "--help") {
  Write-Host "usage: .\install.ps1 [-Target path] [-Bin path] [-Force]"
  exit 0
}
for ($i=0; $i -lt $args.Count; $i++) {
  if ($args[$i] -eq "-Target") { $Target = $args[$i+1]; $i++ }
  elseif ($args[$i] -eq "-Bin") { $Bin = $args[$i+1]; $i++ }
}
$Force = $args -contains "-Force"

$pyExe = "python"
$pyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) { $pyExe = "py"; $pyArgs = @("-3") }
$pyCmd = if ($pyExe -eq "py") { "py -3" } else { "python" }
$version = & $pyExe @pyArgs --version 2>&1
Write-Host $version
if ($version -notmatch "3\.(9|1[0-9])") { Write-Host "Python 3.9+ required"; exit 1 }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Host "warning: ffmpeg not found (timeline / duration checks need it)"
}

if ((Test-Path $Target) -and (-not $Force)) {
  Write-Host "target exists: $Target"
  Write-Host "use -Force to replace it"
  exit 1
}
if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
New-Item -ItemType Directory -Force -Path $Target | Out-Null
New-Item -ItemType Directory -Force -Path $Bin | Out-Null

$items = @("SKILL.md","START_HERE.md","references","scripts","templates","contracts","demo","config","README.md","LICENSE","NOTICE.md")
foreach ($item in $items) {
  $src = Join-Path $Repo $item
  if (-not (Test-Path $src)) { Write-Host "missing: $src"; exit 1 }
  Copy-Item -Recurse -Force $src $Target
}
Write-Host "installed skill: $Target"

$keysDir = Join-Path $HOME ".config\mv-workbench"
New-Item -ItemType Directory -Force -Path $keysDir | Out-Null
$keysFile = Join-Path $keysDir "keys.json"
if (-not (Test-Path $keysFile)) {
  Copy-Item (Join-Path $Repo "config\keys.example.json") $keysFile
  Write-Host "created: $keysFile"
}

$cmd = Join-Path $Bin "mvwb.cmd"
@"
@echo off
$pyCmd "$Target\scripts\mvwb.py" %*
"@ | Set-Content -Encoding ASCII $cmd
Write-Host "installed: $cmd"
Write-Host ""
Write-Host "next:"
Write-Host "  $Bin\mvwb.cmd doctor"
Write-Host "  $Bin\mvwb.cmd demo"
Write-Host "note: add $Bin to PATH, or run $Target\scripts\mvwb.py"
