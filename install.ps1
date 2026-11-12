$ErrorActionPreference = "Stop"
$Repo = $PSScriptRoot
$Target = Join-Path $HOME ".agents\skills"
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
  Write-Host "warning: ffmpeg not found (rough cut / duration checks need it)"
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null
New-Item -ItemType Directory -Force -Path $Bin | Out-Null
$skills = @("zz-mv-gongzuotai","zz-mv-factory","zz-mv-trim","zz-runninghub-cli","ace-music","h3-prompt-writing","zz-manju-image-prompts","muse-router")
foreach ($name in $skills) {
  $src = Join-Path $Repo "skills\$name"
  $dst = Join-Path $Target $name
  if (-not (Test-Path $src)) { Write-Host "missing skill: $src"; exit 1 }
  if ((Test-Path $dst) -and (-not $Force)) {
    Write-Host "skip existing: $dst (use -Force to replace)"
  } else {
    if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
    Copy-Item -Recurse -Force $src $dst
    Write-Host "installed: $dst"
  }
}

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
$pyCmd "$Repo\scripts\mvwb.py" %*
"@ | Set-Content -Encoding ASCII $cmd
Write-Host "installed: $cmd"
Write-Host ""
Write-Host "next:"
Write-Host "  $Repo\mvwb.cmd doctor"
Write-Host "  $Repo\mvwb.cmd demo"
Write-Host "note: add $Bin to PATH, or run $Repo\mvwb.cmd"
