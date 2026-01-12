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



  # where to keep staging copies (used only for read-only sources)

  [string]$StageRoot = "",



  # keep staging folder (debugging)

  [switch]$KeepStage,



  # show foobar window (default: minimized)

  [switch]$ShowFoobar

)



$ErrorActionPreference = "Stop"

function New-ExtSet([string[]]$exts) {

  $set = New-Object "System.Collections.Generic.HashSet[string]" ([StringComparer]::OrdinalIgnoreCase)

  foreach ($eRaw in $exts) {

    if (-not $eRaw) { continue }

    $e = $eRaw.Trim()

    if (-not $e) { continue }

    if ($e[0] -ne '.') { $e = "." + $e }

    $null = $set.Add($e)

  }

  return $set

}



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


function Test-WriteableFolder([string]$folder) {

  try {

    $tmpName = "._th_write_test_" + [Guid]::NewGuid().ToString("N") + ".tmp"

    $tmpPath = Join-Path $folder $tmpName

    $fs = [IO.File]::Open($tmpPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)

    $fs.Close()

    Remove-Item -LiteralPath $tmpPath -Force -ErrorAction SilentlyContinue

    return $true

  } catch {

    return $false

  }

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

  [IO.Directory]::CreateDirectory($stageFolder) | Out-Null



  $dstFiles = New-Object System.Collections.Generic.List[string]

  $dirSet = New-Object "System.Collections.Generic.HashSet[string]" ([StringComparer]::OrdinalIgnoreCase)

  foreach ($f in $files) {

    $rel = Get-RelativePath $releaseFolder $f

    $dest = Join-Path $stageFolder $rel

    $destDir = Split-Path -Parent $dest

    if ($dirSet.Add($destDir)) {

      [IO.Directory]::CreateDirectory($destDir) | Out-Null

    }

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


  $log = Find-NewLog -folder $folder -startTime $startTime -nameRegex $nameRegex

  if ($log) { return $log }



  $watcher = $null

  $useWatcher = $false

  try {

    $watcher = New-Object System.IO.FileSystemWatcher

    $watcher.Path = $folder

    $watcher.IncludeSubdirectories = $true

    $watcher.Filter = "*"

    $watcher.NotifyFilter = [IO.NotifyFilters]'FileName, LastWrite, CreationTime'

    $watcher.EnableRaisingEvents = $true

    $useWatcher = $true

  } catch {

    $useWatcher = $false

  }



  while ((Get-Date) -lt $deadline) {

    if ($useWatcher) {

      $remainingMs = [int][Math]::Max(1, ($deadline - (Get-Date)).TotalMilliseconds)

      $waitMs = [int][Math]::Min(1000, $remainingMs)

      $null = $watcher.WaitForChanged([IO.WatcherChangeTypes]::All, $waitMs)

    } else {

      Start-Sleep -Seconds 1

    }



    $log = Find-NewLog -folder $folder -startTime $startTime -nameRegex $nameRegex

    if ($log) {

      if ($watcher) { $watcher.Dispose() }

      return $log

    }

    $sec++

    if ($sec % 5 -eq 0) {

      $mm = [int]($sec / 60)

      $ss = $sec % 60

      Write-Host -NoNewline (" [{0:00}:{1:00}]" -f $mm, $ss)

    } else {

      Write-Host -NoNewline "."

    }

  }



  if ($watcher) { $watcher.Dispose() }

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

[IO.Directory]::CreateDirectory($OutDir) | Out-Null



if (-not $StageRoot) {

  $StageRoot = Join-Path $env:TEMP "fb2k_dr_stage"

}



Write-Host "Root:     $rootResolved"

Write-Host "Foobar:   $fb2k"

Write-Host "OutDir:   $OutDir"

Write-Host "StageRoot $StageRoot (read-only only)"

Write-Host "Cmd:      $CommandName"

Write-Host ""



$ExtSet = New-ExtSet $Ext

$stageRootReady = $false

$relFolders = Get-ReleaseFolders $rootResolved $Groups



foreach ($rf in $relFolders) {

  $releaseFolder = $rf.FullName

  $releaseName = Split-Path $releaseFolder -Leaf



  $srcAudio = Get-ChildItem -LiteralPath $releaseFolder -Recurse -File -ErrorAction SilentlyContinue |

    Where-Object { $ExtSet.Contains($_.Extension) } |

    Sort-Object FullName |

    Select-Object -ExpandProperty FullName



  if (-not $srcAudio -or $srcAudio.Count -eq 0) {

    Write-Host ("SKIP (no audio): " + $releaseName)

    continue

  }



  $useStage = -not (Test-WriteableFolder $releaseFolder)

  if ($useStage) {

    if (-not $stageRootReady) {

      [IO.Directory]::CreateDirectory($StageRoot) | Out-Null

      $stageRootReady = $true

    }

    Write-Host ("DR scan: {0} ({1} tracks) [read-only -> staging]" -f $releaseName, $srcAudio.Count)

    # stage to a local folder (log cannot be created on read-only)

    $stageFolder = Join-Path $StageRoot (Sanitize-FileName $releaseName)

    Write-Host ("  staging -> " + $stageFolder)

    $scanAudio = Copy-ReleaseToStage -releaseFolder $releaseFolder -files $srcAudio -stageFolder $stageFolder

    $logFolder = $stageFolder

    # remove old logs from staging (avoid picking up stale ones)

    Get-ChildItem -LiteralPath $stageFolder -Recurse -File -ErrorAction SilentlyContinue |

      Where-Object { $_.Name -match $LogNameRegex } |

      Remove-Item -Force -ErrorAction SilentlyContinue

  } else {

    Write-Host ("DR scan: {0} ({1} tracks) [direct]" -f $releaseName, $srcAudio.Count)

    $scanAudio = $srcAudio

    $logFolder = $releaseFolder

  }



  $start = Get-Date

  Start-DrScan -fb2k $fb2k -cmdName $CommandName -files $scanAudio -show:$ShowFoobar



  Write-Host -NoNewline "  waiting log "

  $log = Wait-ForLog -folder $logFolder -startTime $start -timeoutSec $TimeoutSec -nameRegex $LogNameRegex

  Write-Host ""



  if (-not $log) {

    Write-Warning "  Log did not appear. Usually this means DR Meter automatic log writing is OFF. (Changelog mentions a separate auto log writing setting.) :contentReference[oaicite:4]{index=4}"

    Write-Warning "  For diagnostics: run with -LogNameRegex '.*\\.(txt|log)$' and see what files are created."

    if ($useStage -and -not $KeepStage) {

      Remove-Item -LiteralPath $stageFolder -Recurse -Force -ErrorAction SilentlyContinue

    }

    break

  }



  $outName = (Sanitize-FileName $releaseName) + "_dr.txt"

  $dest = Join-Path $OutDir $outName

  Copy-Item -LiteralPath $log.FullName -Destination $dest -Force

  Write-Host ("  -> " + $dest)



  if ($useStage -and -not $KeepStage) {

    Remove-Item -LiteralPath $stageFolder -Recurse -Force -ErrorAction SilentlyContinue

  }

}
