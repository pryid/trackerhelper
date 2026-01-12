param(

  [Parameter(Mandatory = $true)]

  [string]$Root,



  # if foobar is portable, set the path explicitly

  [string]$FoobarPath = "",



  # from your screenshot (important: ONLY the final command name)

  [string]$CommandName = "Measure Dynamic Range",



  # if you use Albums/* and Singles/* structure

  [string[]]$Groups = @("Albums", "Singles"),



  # which files are treated as tracks

  [string[]]$Ext = @(".flac",".mp3",".m4a",".aac",".ogg",".opus",".wav",".wma",".aiff",".aif",".alac"),



  # max wait for a log per release (seconds)

  [int]$TimeoutSec = 1800,



  # default log name (if not matched, see hints below)

  [string]$LogNameRegex = "^foo_dr.*\.(txt|log)$",



  # where to save final reports

  [string]$OutDir = "",



  # where to keep staging copies (local only)

  [string]$StageRoot = "",



  # keep staging folder (debugging)

  [switch]$KeepStage,



  # show foobar window (default: minimized)

  [switch]$ShowFoobar

)



$ErrorActionPreference = "Stop"



function Resolve-Foobar([string]$Provided) {

  if ($Provided -and (Test-Path -LiteralPath $Provided)) {

    return (Resolve-Path -LiteralPath $Provided).ProviderPath

  }



  # try standard locations

  $pf = $env:ProgramFiles

  $pf86 = ${env:ProgramFiles(x86)}



  $cands = @()

  if ($pf)   { $cands += (Join-Path $pf "foobar2000\foobar2000.exe") }

  if ($pf86) { $cands += (Join-Path $pf86 "foobar2000\foobar2000.exe") }



  $exe = $cands | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1

  if ($exe) { return (Resolve-Path -LiteralPath $exe).ProviderPath }



  throw "foobar2000.exe not found. Set -FoobarPath 'C:\\Path\\to\\foobar2000.exe'"

}



function Sanitize-FileName([string]$name) {

  $bad = '[\\\/:\*\?"<>|]'

  $out = ($name -replace $bad, "_").Trim()

  if (-not $out) { $out = "release" }

  return $out

}



function Get-ReleaseFolders([string]$rootPath, [string[]]$groups) {

  $rootItem = Get-Item -LiteralPath $rootPath



  $groupDirs = @()

  foreach ($g in $groups) {

    $p = Join-Path $rootItem.FullName $g

    if (Test-Path -LiteralPath $p) { $groupDirs += $p }

  }



  if ($groupDirs.Count -gt 0) {

    $rels = foreach ($gd in $groupDirs) {

      Get-ChildItem -LiteralPath $gd -Directory -ErrorAction SilentlyContinue

    }

    return $rels | Sort-Object FullName

  }



  return (Get-ChildItem -LiteralPath $rootItem.FullName -Directory -ErrorAction SilentlyContinue | Sort-Object FullName)

}



function Get-RelativePath([string]$fromDir, [string]$toPath) {

  $base = $fromDir.TrimEnd('\') + '\'

  $fromUri = New-Object System.Uri($base)

  $toUri = New-Object System.Uri($toPath)

  $relUri = $fromUri.MakeRelativeUri($toUri)

  return [System.Uri]::UnescapeDataString($relUri.ToString()).Replace('/', '\')

}



function Quote-Arg([string]$s) {

  # foobar cmdline accepts plain quotes; escape inner quotes

  return '"' + ($s -replace '"','\"') + '"'

}



function Copy-ReleaseToStage([string]$releaseFolder, [string[]]$files, [string]$stageFolder) {

  if (Test-Path -LiteralPath $stageFolder) {

    Remove-Item -LiteralPath $stageFolder -Recurse -Force

  }

  New-Item -ItemType Directory -Path $stageFolder -Force | Out-Null



  $dstFiles = New-Object System.Collections.Generic.List[string]

  foreach ($f in $files) {

    $rel = Get-RelativePath $releaseFolder $f

    $dest = Join-Path $stageFolder $rel

    $destDir = Split-Path -Parent $dest

    New-Item -ItemType Directory -Path $destDir -Force | Out-Null

    Copy-Item -LiteralPath $f -Destination $dest -Force

    $dstFiles.Add($dest)

  }

  return ,$dstFiles.ToArray()

}



function Find-NewLog([string]$folder, [datetime]$startTime, [string]$nameRegex) {

  Get-ChildItem -LiteralPath $folder -Recurse -File -ErrorAction SilentlyContinue |

    Where-Object { $_.LastWriteTime -ge $startTime -and $_.Name -match $nameRegex } |

    Sort-Object LastWriteTime -Descending |

    Select-Object -First 1

}



function Wait-ForLog([string]$folder, [datetime]$startTime, [int]$timeoutSec, [string]$nameRegex) {

  $deadline = (Get-Date).AddSeconds($timeoutSec)

  $sec = 0



  while ((Get-Date) -lt $deadline) {

    $log = Find-NewLog -folder $folder -startTime $startTime -nameRegex $nameRegex

    if ($log) { return $log }



    Start-Sleep -Seconds 1

    $sec++

    if ($sec % 5 -eq 0) {

      $mm = [int]($sec / 60)

      $ss = $sec % 60

      Write-Host -NoNewline (" [{0:00}:{1:00}]" -f $mm, $ss)

    } else {

      Write-Host -NoNewline "."

    }

  }



  return $null

}



function Start-DrScan([string]$fb2k, [string]$cmdName, [string[]]$files, [switch]$show) {

  # /context_command:<context menu command> <files> :contentReference[oaicite:2]{index=2}

  # + /immediate to avoid waiting for sorting/add delay :contentReference[oaicite:3]{index=3}

  $cmdSwitch = "/context_command:" + (Quote-Arg $cmdName)

  $fileArgs = ($files | ForEach-Object { Quote-Arg $_ }) -join " "

  $argString = "/immediate $cmdSwitch $fileArgs"



  $ws = "Minimized"

  if ($show) { $ws = "Normal" }



  Start-Process -FilePath $fb2k -ArgumentList $argString -WindowStyle $ws | Out-Null

}



# --- main ---

$rootResolved = (Resolve-Path -LiteralPath $Root).ProviderPath

$fb2k = Resolve-Foobar $FoobarPath



if (-not $OutDir) {

  $myMusic = [Environment]::GetFolderPath([Environment+SpecialFolder]::MyMusic)

  $OutDir = Join-Path $myMusic "DR"

}

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null



if (-not $StageRoot) {

  $StageRoot = Join-Path $env:TEMP "fb2k_dr_stage"

}

New-Item -ItemType Directory -Path $StageRoot -Force | Out-Null



Write-Host "Root:     $rootResolved"

Write-Host "Foobar:   $fb2k"

Write-Host "OutDir:   $OutDir"

Write-Host "StageRoot $StageRoot"

Write-Host "Cmd:      $CommandName"

Write-Host ""



$relFolders = Get-ReleaseFolders $rootResolved $Groups



foreach ($rf in $relFolders) {

  $releaseFolder = $rf.FullName

  $releaseName = Split-Path $releaseFolder -Leaf



  $srcAudio = Get-ChildItem -LiteralPath $releaseFolder -Recurse -File -ErrorAction SilentlyContinue |

    Where-Object { $Ext -contains $_.Extension.ToLower() } |

    Sort-Object FullName |

    Select-Object -ExpandProperty FullName



  if (-not $srcAudio -or $srcAudio.Count -eq 0) {

    Write-Host ("SKIP (no audio): " + $releaseName)

    continue

  }



  Write-Host ("DR scan: {0} ({1} tracks) [SMB read-only -> staging]" -f $releaseName, $srcAudio.Count)



  # stage to a local folder (log cannot be created on read-only)

  $stageFolder = Join-Path $StageRoot (Sanitize-FileName $releaseName)

  Write-Host ("  staging -> " + $stageFolder)

  $stageAudio = Copy-ReleaseToStage -releaseFolder $releaseFolder -files $srcAudio -stageFolder $stageFolder



  # remove old logs from staging (avoid picking up stale ones)

  Get-ChildItem -LiteralPath $stageFolder -Recurse -File -ErrorAction SilentlyContinue |

    Where-Object { $_.Name -match $LogNameRegex } |

    Remove-Item -Force -ErrorAction SilentlyContinue



  $start = Get-Date

  Start-DrScan -fb2k $fb2k -cmdName $CommandName -files $stageAudio -show:$ShowFoobar



  Write-Host -NoNewline "  waiting log "

  $log = Wait-ForLog -folder $stageFolder -startTime $start -timeoutSec $TimeoutSec -nameRegex $LogNameRegex

  Write-Host ""



  if (-not $log) {

    Write-Warning "  Log did not appear. Usually this means DR Meter automatic log writing is OFF. (Changelog mentions a separate auto log writing setting.) :contentReference[oaicite:4]{index=4}"

    Write-Warning "  For diagnostics: run with -LogNameRegex '.*\\.(txt|log)$' and see what files are created."

    if (-not $KeepStage) { Remove-Item -LiteralPath $stageFolder -Recurse -Force -ErrorAction SilentlyContinue }

    break

  }



  $outName = (Sanitize-FileName $releaseName) + "_dr.txt"

  $dest = Join-Path $OutDir $outName

  Copy-Item -LiteralPath $log.FullName -Destination $dest -Force

  Write-Host ("  -> " + $dest)



  if (-not $KeepStage) {

    Remove-Item -LiteralPath $stageFolder -Recurse -Force -ErrorAction SilentlyContinue

  }

}
