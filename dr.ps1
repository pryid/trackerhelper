param(

  [Parameter(Mandatory = $true)]

  [string]$Root,



  # если foobar portable — укажи явно

  [string]$FoobarPath = "",



  # по твоему скрину (важно: ТОЛЬКО конечное имя команды)

  [string]$CommandName = "Measure Dynamic Range",



  # если структура Albums/* и Singles/*

  [string[]]$Groups = @("Albums", "Singles"),



  # какие файлы считать треками

  [string[]]$Ext = @(".flac",".mp3",".m4a",".aac",".ogg",".opus",".wav",".wma",".aiff",".aif",".alac"),



  # максимум ждать появления лога на один релиз (сек)

  [int]$TimeoutSec = 1800,



  # как обычно называется лог (если не ловит — см. подсказку ниже)

  [string]$LogNameRegex = "^foo_dr.*\.(txt|log)$",



  # куда сохранять итоговые отчёты

  [string]$OutDir = "",



  # где держать временные копии релизов (локально!)

  [string]$StageRoot = "",



  # не удалять временную копию релиза (для дебага)

  [switch]$KeepStage,



  # показать окно foobar (по умолчанию minimized)

  [switch]$ShowFoobar

)



$ErrorActionPreference = "Stop"



function Resolve-Foobar([string]$Provided) {

  if ($Provided -and (Test-Path -LiteralPath $Provided)) {

    return (Resolve-Path -LiteralPath $Provided).ProviderPath

  }



  # пробуем стандартные места

  $pf = $env:ProgramFiles

  $pf86 = ${env:ProgramFiles(x86)}



  $cands = @()

  if ($pf)   { $cands += (Join-Path $pf "foobar2000\foobar2000.exe") }

  if ($pf86) { $cands += (Join-Path $pf86 "foobar2000\foobar2000.exe") }



  $exe = $cands | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1

  if ($exe) { return (Resolve-Path -LiteralPath $exe).ProviderPath }



  throw "Не нашёл foobar2000.exe. Укажи -FoobarPath 'C:\Path\to\foobar2000.exe'"

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

  # для cmdline foobar достаточно обычных кавычек; экранируем внутренние "

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

  # + /immediate чтобы не ждать сортировку/задержку добавления :contentReference[oaicite:3]{index=3}

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



  # стейджим в локальную папку (иначе лог не создать на read-only)

  $stageFolder = Join-Path $StageRoot (Sanitize-FileName $releaseName)

  Write-Host ("  staging -> " + $stageFolder)

  $stageAudio = Copy-ReleaseToStage -releaseFolder $releaseFolder -files $srcAudio -stageFolder $stageFolder



  # чистим старые логи в stage (чтобы не схватить “старьё”)

  Get-ChildItem -LiteralPath $stageFolder -Recurse -File -ErrorAction SilentlyContinue |

    Where-Object { $_.Name -match $LogNameRegex } |

    Remove-Item -Force -ErrorAction SilentlyContinue



  $start = Get-Date

  Start-DrScan -fb2k $fb2k -cmdName $CommandName -files $stageAudio -show:$ShowFoobar



  Write-Host -NoNewline "  waiting log "

  $log = Wait-ForLog -folder $stageFolder -startTime $start -timeoutSec $TimeoutSec -nameRegex $LogNameRegex

  Write-Host ""



  if (-not $log) {

    Write-Warning "  Лог не появился. Обычно это значит, что в DR Meter НЕ включено automatic log writing. (В changelog упоминается отдельная настройка auto log writing.) :contentReference[oaicite:4]{index=4}"

    Write-Warning "  Для диагностики: запусти с -LogNameRegex '.*\.(txt|log)$' и посмотри, что реально создаётся."

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

