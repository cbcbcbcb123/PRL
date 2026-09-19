param([switch]$ExecuteApproved, [switch]$ResumeApprovedFallback)
$ErrorActionPreference = 'Stop'
$repairRoot = 'E:\Temp-Projects\PRL\project_control\evidence\docker_recovery_20260919_v01'
$manifestPath = Join-Path $repairRoot 'frozen_manifest.json'
$authorizationPath = Join-Path $repairRoot 'authorization.md'
$auditPath = Join-Path $repairRoot 'execution.jsonl'
$expectedManifestHash = '9f281fabde61c7fa2f7a3d0fee90e92303f3297983fbbb58cce2806b68439cd7'
$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLower()
if ($manifestHash -ne $expectedManifestHash) { throw 'Frozen manifest hash mismatch' }
$repairManifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$authorization = Get-Content -LiteralPath $authorizationPath -Raw
if (-not $authorization.Contains($expectedManifestHash) -or -not $authorization.Contains('批准该精确范围')) {
    throw 'Exact authorization record missing'
}
if (Test-Path -LiteralPath $auditPath) {
    if (-not $ResumeApprovedFallback) { throw 'Attempt already registered; no automatic replay' }
    $priorEvents = @(Get-Content -LiteralPath $auditPath | ForEach-Object { $_ | ConvertFrom-Json })
    $interruption = Get-Content -LiteralPath (Join-Path $repairRoot 'graceful_stop_interruption.json') -Raw | ConvertFrom-Json
    if ($priorEvents.Count -ne 1 -or $priorEvents[0].event -ne 'authorized_attempt_registered' -or
        $interruption.postcheck.directory_moves -ne 0 -or $interruption.postcheck.desktop_starts -ne 0) {
        throw 'Not the verified zero-move zero-start graceful-timeout fallback point'
    }
} elseif ($ResumeApprovedFallback) { throw 'No registered attempt to continue' }

function Write-RepairEvent([string]$eventName, $eventData) {
    $eventRecord = [ordered]@{time_utc=(Get-Date).ToUniversalTime().ToString('o'); event=$eventName; data=$eventData}
    $eventLine = $eventRecord | ConvertTo-Json -Depth 10 -Compress
    [IO.File]::AppendAllText($auditPath, $eventLine+[Environment]::NewLine, [Text.UTF8Encoding]::new($false))
    Write-Output $eventLine
}

function Assert-NoLinkedParents([string]$directoryPath) {
    $directoryCursor = Get-Item -LiteralPath $directoryPath -Force
    while ($null -ne $directoryCursor) {
        if (($directoryCursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw ('Directory link not allowed: '+$directoryCursor.FullName)
        }
        $directoryCursor = $directoryCursor.Parent
    }
}

function Assert-DirectoryMetadata($targetRecord, [string]$currentPath) {
    $currentRoot = Get-Item -LiteralPath $currentPath -Force
    if ([string]$currentRoot.Attributes -ne $targetRecord.source_attributes -or
        $currentRoot.CreationTimeUtc.Ticks -ne ([DateTimeOffset]$targetRecord.source_created_utc).UtcDateTime.Ticks -or
        $currentRoot.LastWriteTimeUtc.Ticks -ne ([DateTimeOffset]$targetRecord.source_modified_utc).UtcDateTime.Ticks) {
        throw ('Root identity/metadata changed: '+$currentPath)
    }
    $currentChildren = @(Get-ChildItem -LiteralPath $currentPath -Force)
    if ($currentChildren.Count -ne $targetRecord.entries.Count) { throw 'Runtime entry count changed' }
    foreach ($expectedEntry in $targetRecord.entries) {
        $entryName = [IO.Path]::GetFileName($expectedEntry.FullName)
        $matchingChildren = @($currentChildren | Where-Object { $_.Name -ceq $entryName })
        if ($matchingChildren.Count -ne 1) { throw ('Runtime entry changed: '+$entryName) }
        $currentEntry = $matchingChildren[0]
        if ($currentEntry.PSIsContainer -or $currentEntry.Length -ne $expectedEntry.Length -or
            [int]$currentEntry.Attributes -ne $expectedEntry.Attributes -or
            $currentEntry.CreationTimeUtc.Ticks -ne ([DateTimeOffset]$expectedEntry.CreationTimeUtc).UtcDateTime.Ticks -or
            $currentEntry.LastWriteTimeUtc.Ticks -ne ([DateTimeOffset]$expectedEntry.LastWriteTimeUtc).UtcDateTime.Ticks) {
            throw ('Runtime object metadata changed: '+$entryName)
        }
    }
}

function Assert-TargetBeforeMove($targetRecord) {
    $exactAllowedSources = @('C:\Users\chenb\AppData\Local\Docker\run',
                            'C:\Users\chenb\AppData\Local\docker-secrets-engine')
    $sourcePath = [IO.Path]::GetFullPath($targetRecord.source)
    $destinationPath = [IO.Path]::GetFullPath($targetRecord.destination)
    if ($sourcePath -cne $targetRecord.source -or $sourcePath -cnotin $exactAllowedSources -or
        $destinationPath -cne ($sourcePath+'.quarantine-20260919-repair-v01') -or
        [IO.Path]::GetDirectoryName($sourcePath) -cne [IO.Path]::GetDirectoryName($destinationPath)) {
        throw 'Target outside exact two-path authorization'
    }
    Assert-NoLinkedParents $sourcePath
    if (Test-Path -LiteralPath $destinationPath) { throw ('Destination exists: '+$destinationPath) }
    Assert-DirectoryMetadata $targetRecord $sourcePath
}

function Get-CheckedDockerProcesses {
    $currentProcesses = @(Get-CimInstance Win32_Process -Filter "Name='Docker Desktop.exe' OR Name='com.docker.backend.exe' OR Name='com.docker.build.exe'")
    foreach ($currentProcess in $currentProcesses) {
        $matchingIdentities = @($repairManifest.stopped_processes_if_needed | Where-Object { $_.ProcessId -eq $currentProcess.ProcessId })
        if ($matchingIdentities.Count -ne 1) { throw 'Unexpected Docker process; scope changed' }
        $approvedIdentity = $matchingIdentities[0]
        if ($currentProcess.ExecutablePath -cne $approvedIdentity.ExecutablePath -or
            ([DateTimeOffset]$currentProcess.CreationDate).UtcDateTime.Ticks -ne ([DateTimeOffset]$approvedIdentity.CreationDate).UtcDateTime.Ticks) {
            throw 'Docker PID was reused or identity changed'
        }
    }
    return $currentProcesses
}

function Assert-ProtectedFiles {
    foreach ($protectedFile in $repairManifest.protected_file_facts) {
        if ((Get-FileHash -LiteralPath $protectedFile.path -Algorithm SHA256).Hash.ToLower() -ne $protectedFile.sha256) {
            throw ('Protected file hash changed: '+$protectedFile.path)
        }
    }
    $protectedWsl = Get-Item -LiteralPath $repairManifest.protected_wsl_metadata.path -Force
    if ([string]$protectedWsl.Attributes -ne 'Directory') { throw 'Protected WSL root missing or linked' }
}

foreach ($targetRecord in $repairManifest.targets) { Assert-TargetBeforeMove $targetRecord }
$initialProcesses = @(Get-CheckedDockerProcesses)
Assert-ProtectedFiles
if (-not $ExecuteApproved) {
    [ordered]@{status='passed';mode='read_only_preflight';targets=$repairManifest.targets.Count;
        listed_processes_present=$initialProcesses.Count;manifest_sha256=$manifestHash} | ConvertTo-Json -Compress
    exit 0
}

# Create-only, durable registration before the first state change.
if (-not $ResumeApprovedFallback) {
    $auditHandle = [IO.File]::Open($auditPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    $auditHandle.Dispose()
}
try {
    if ($ResumeApprovedFallback) {
        $taskCliRemnants = @(Get-CimInstance Win32_Process -Filter "ProcessId=46884 OR ProcessId=5752")
        if ($taskCliRemnants.Count -ne 0) { throw 'Interrupted task CLI still exists; stop' }
        Write-RepairEvent 'approved_fallback_after_cli_timeout' @{graceful_stop_invocations=1;no_extra_process_scope=$true}
    } else {
        Write-RepairEvent 'authorized_attempt_registered' @{manifest_sha256=$manifestHash; scientific_execution='not_run'}
        $stopOutput = (& docker desktop stop --timeout 30 2>&1 | Out-String)
        $stopExitCode = $LASTEXITCODE
        Write-RepairEvent 'single_graceful_stop' @{exit_code=$stopExitCode;output=$stopOutput}
    }
    $remainingProcesses = @(Get-CheckedDockerProcesses)
    foreach ($remainingProcess in $remainingProcesses) {
        # Read identity once more immediately before the specifically approved stop.
        $verifiedProcesses = @(Get-CheckedDockerProcesses)
        if (@($verifiedProcesses | Where-Object { $_.ProcessId -eq $remainingProcess.ProcessId }).Count -eq 1) {
            Stop-Process -Id $remainingProcess.ProcessId -Force -ErrorAction Stop
            Write-RepairEvent 'listed_process_stopped' @{process_id=$remainingProcess.ProcessId;executable=$remainingProcess.ExecutablePath}
        }
    }
    Start-Sleep -Milliseconds 1500
    if (@(Get-CheckedDockerProcesses).Count -ne 0) { throw 'Docker processes remain; do not move directories' }
    Assert-ProtectedFiles
    foreach ($targetRecord in $repairManifest.targets) { Assert-TargetBeforeMove $targetRecord }
    foreach ($targetRecord in $repairManifest.targets) {
        Assert-TargetBeforeMove $targetRecord
        Write-RepairEvent 'before_authorized_directory_move' @{source=$targetRecord.source;destination=$targetRecord.destination}
        [System.IO.Directory]::Move($targetRecord.source, $targetRecord.destination)
        Write-RepairEvent 'directory_move_returned' @{source=$targetRecord.source;destination=$targetRecord.destination}
        if (Test-Path -LiteralPath $targetRecord.source) { throw 'Source exists again after move; new target requires decision' }
        Assert-NoLinkedParents $targetRecord.destination
        Assert-DirectoryMetadata $targetRecord $targetRecord.destination
        Write-RepairEvent 'directory_move_verified' @{source_absent=$true;destination=$targetRecord.destination;objects=$targetRecord.entries.Count}
    }
    foreach ($targetRecord in $repairManifest.targets) {
        if (Test-Path -LiteralPath $targetRecord.source) { throw 'Runtime root reappeared before start' }
    }
    if (@(Get-CheckedDockerProcesses).Count -ne 0) { throw 'Unexpected Docker restart before authorized launch' }
    Assert-ProtectedFiles
    Write-RepairEvent 'one_start_authority_consumed' @{executable=$repairManifest.restart.executable;maximum_starts=1}
    $launchedDesktop = Start-Process -FilePath $repairManifest.restart.executable -WindowStyle Hidden -PassThru
    Write-RepairEvent 'desktop_start_returned' @{process_id=$launchedDesktop.Id;startup_count=1;validation_status='not_run'}
} catch {
    Write-RepairEvent 'stopped_on_failure' @{error=$_.Exception.Message;no_retry=$true;scientific_execution='not_run'}
    exit 2
}
