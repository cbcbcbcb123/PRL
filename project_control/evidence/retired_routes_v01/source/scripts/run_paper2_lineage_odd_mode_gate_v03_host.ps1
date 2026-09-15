param(
    [string]$ProjectRoot = "E:\Temp-Projects\PRL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$containerName = "prl-paper2-lineage-odd-mode-gate-v03-20260909"
$imageName = "dolfinx/dolfinx:v0.11.0"
$expectedImageId = "sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"
$baseCommit = "b45650a9e370be138a70acf305b6c3a21e6a7ed2"
$runnerHash = "d6e52b17e00d9e0ddafbaee86689917f8f2bb4755fdd3d1cbc02ba8d1cf24ed7"
$resultDirectory = Join-Path $ProjectRoot "results\paper2_lineage_odd_mode_gate\v03_20260909"
$summaryPath = Join-Path $resultDirectory "summary.json"
$watchdogFailurePath = Join-Path $resultDirectory "host_watchdog_failure.json"

if ((Resolve-Path -LiteralPath $ProjectRoot).Path -ne "E:\Temp-Projects\PRL") {
    throw "project root drift"
}
if (Test-Path -LiteralPath $resultDirectory) {
    throw "create-only result directory already exists"
}

$desktopStatus = (& docker desktop status 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0 -or $desktopStatus -notmatch "running") {
    throw "Docker Desktop is not running; P1 v03 remains NOT_RUN"
}
$actualImageId = (& docker image inspect $imageName --format "{{.Id}}" 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $actualImageId -ne $expectedImageId) {
    throw "container image identity preflight failed"
}
$existingContainer = (& docker ps --all --filter "name=^$containerName`$" --format "{{.ID}}" 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "container-name preflight failed"
}
if ($existingContainer) {
    throw "frozen container name already exists"
}

New-Item -ItemType Directory -Path $resultDirectory | Out-Null

$createArguments = @(
    "create",
    "--name", $containerName,
    "--network", "none",
    "--cpus", "1",
    "--memory", "8g",
    "--memory-swap", "8g",
    "--pids-limit", "256",
    "--read-only",
    "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
    "--tmpfs", "/root/.cache:rw,exec,nosuid,nodev,size=536870912",
    "--mount", "type=bind,src=$ProjectRoot,dst=/workspace,readonly",
    "--mount", "type=bind,src=$resultDirectory,dst=/output",
    "--workdir", "/workspace",
    "--env", "OMP_NUM_THREADS=1",
    "--env", "OPENBLAS_NUM_THREADS=1",
    "--env", "MKL_NUM_THREADS=1",
    "--env", "NUMEXPR_NUM_THREADS=1",
    "--env", "PAPER2_IMAGE_ID=$expectedImageId",
    "--env", "PAPER2_CONTAINER_NAME=$containerName",
    "--env", "PAPER2_EXTERNAL_WATCHDOG=host-60s-v01",
    "--env", "PYTHONPATH=/workspace/src:/usr/local/dolfinx-real/lib/python3.12/dist-packages:/usr/local/lib:",
    "--entrypoint", "python3",
    $imageName,
    "/workspace/scripts/run_paper2_lineage_odd_mode_gate_v03.py",
    "--output", "/output/summary.json",
    "--base-commit", $baseCommit,
    "--runner-sha256", $runnerHash
)

$createdContainerId = (& docker @createArguments 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $createdContainerId) {
    throw "container creation failed before the formal attempt started"
}

$dockerExecutable = (Get-Command docker).Source
$attachProcess = Start-Process -FilePath $dockerExecutable -ArgumentList @(
    "start", "--attach", $containerName
) -WindowStyle Hidden -PassThru
$finishedWithinBudget = $attachProcess.WaitForExit(60000)

if (-not $finishedWithinBudget) {
    & docker stop --time 1 $containerName | Out-Null
    if (-not $attachProcess.HasExited) {
        Stop-Process -Id $attachProcess.Id
    }
    $failureRecord = [ordered]@{
        schema = "paper2_lineage_odd_mode_gate_host_watchdog_failure.v1"
        status = "FAILED_CLOSED"
        execution_status = "FAIL"
        scientific_status = "NOT_EVALUABLE_DUE_TO_EXECUTION_FAILURE"
        reason = "external host watchdog exceeded 60 seconds"
        formal_attempt_consumed = $true
        container_name = $containerName
        runner_sha256 = $runnerHash
        created_at = (Get-Date).ToString("o")
    }
    $failureRecord | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $watchdogFailurePath -Encoding UTF8
    throw "formal P1 v03 attempt exceeded the independent 60-second watchdog"
}

$containerExitCodeText = (& docker inspect $containerName --format "{{.State.ExitCode}}" 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "could not inspect the completed container"
}
if (-not (Test-Path -LiteralPath $summaryPath)) {
    throw "formal attempt completed without the required summary.json"
}

$containerExitCode = [int]$containerExitCodeText
Write-Output "P1 v03 container exit code: $containerExitCode"
Write-Output "Summary: $summaryPath"
exit $containerExitCode
