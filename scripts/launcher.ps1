# ============================================================================
# RoadSoS - Windows Launcher Orchestrator
# PowerShell 5.1 compatible. Direct process execution only.
# ============================================================================

param(
    [switch]$DebugMode,
    [string]$LogPrefix = "startup"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$script:ScriptDir = Split-Path -Parent $PSCommandPath
$script:RootDir = Split-Path -Parent $script:ScriptDir
$script:BackendDir = Join-Path $script:RootDir "backend"
$script:FrontendDir = Join-Path $script:RootDir "frontend"
$script:LogDir = Join-Path $script:RootDir "logs"
$script:BackendPort = 8000
$script:FrontendPort = 5173
$script:BackendUrl = "http://127.0.0.1:{0}" -f $script:BackendPort
$script:FrontendUrl = "http://127.0.0.1:{0}" -f $script:FrontendPort
$script:BackendProcess = $null
$script:FrontendProcess = $null
$script:PythonExe = $null
$script:VenvPython = Join-Path $script:BackendDir ".venv\Scripts\python.exe"
$script:NpmExe = $null
$script:ExitCode = 1

. (Join-Path $script:ScriptDir "logger.ps1")
. (Join-Path $script:ScriptDir "healthcheck.ps1")

function Show-Banner {
    $mode = if ($DebugMode) { "DEBUG" } else { "STANDARD" }
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " RoadSoS - Emergency Response Intelligence Platform" -ForegroundColor Cyan
    Write-Host (" Mode: {0}" -f $mode) -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Resolve-RequiredCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$InstallHint
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw ("Required command not found: {0}. {1}" -f $Name, $InstallHint)
    }

    Write-Log -Level OK -Message ("Found {0}: {1}" -f $Name, $command.Source)
    return $command.Source
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$Arguments = @(),

        [string]$WorkingDirectory = $script:RootDir,

        [switch]$AllowFailure
    )

    Write-Log -Level DEBUG -Message ("Running {0}: {1} {2}" -f $Name, $FilePath, ($Arguments -join " "))
    Push-Location $WorkingDirectory
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
        Pop-Location
    }

    if ($null -eq $exitCode) {
        $exitCode = 0
    }

    Write-CommandResult -Name $Name -ExitCode $exitCode -Output $output

    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw ("Command failed: {0} exited with code {1}" -f $Name, $exitCode)
    }

    return @{
        ExitCode = $exitCode
        Output   = $output
    }
}

function Get-PortProcessIds {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $ids = @()

    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        foreach ($connection in $connections) {
            if ($connection.OwningProcess -and $ids -notcontains $connection.OwningProcess) {
                $ids += [int]$connection.OwningProcess
            }
        }
    } catch {
        $lines = & netstat -ano 2>$null
        foreach ($line in $lines) {
            if ($line -match (":{0}\s" -f $Port) -and $line -match "LISTENING") {
                $parts = $line -split "\s+" | Where-Object { $_ -ne "" }
                if ($parts.Count -gt 0) {
                    $candidate = 0
                    if ([int]::TryParse($parts[$parts.Count - 1], [ref]$candidate)) {
                        if ($ids -notcontains $candidate) {
                            $ids += $candidate
                        }
                    }
                }
            }
        }
    }

    return $ids
}

function Stop-ProcessOnPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $ids = Get-PortProcessIds -Port $Port
    foreach ($id in $ids) {
        try {
            $process = Get-Process -Id $id -ErrorAction Stop
            Write-Log -Level WARN -Message ("Stopping {0} (PID {1}) on port {2}" -f $process.ProcessName, $id, $Port)
            Stop-Process -Id $id -Force -ErrorAction Stop
        } catch {
            Write-Log -Level WARN -Message ("Could not stop PID {0} on port {1}: {2}" -f $id, $Port, $_.Exception.Message)
        }
    }
}

function Clear-RoadSoSPorts {
    Write-Log -Level STEP -Message "Clearing occupied RoadSoS ports"
    Stop-ProcessOnPort -Port $script:BackendPort
    Stop-ProcessOnPort -Port $script:FrontendPort
    Start-Sleep -Seconds 2

    foreach ($port in @($script:BackendPort, $script:FrontendPort)) {
        $remaining = @(Get-PortProcessIds -Port $port)
        if ($remaining.Count -gt 0) {
            throw ("Port {0} is still occupied by PID(s): {1}" -f $port, ($remaining -join ", "))
        }
    }

    Write-Log -Level OK -Message "Required ports are available"
}

function Validate-Environment {
    Write-Log -Level STEP -Message "1/7 Validate environment"
    $script:PythonExe = Resolve-RequiredCommand -Name "python" -InstallHint "Install Python 3.11+ and add it to PATH."
    $script:NpmExe = Resolve-RequiredCommand -Name "npm.cmd" -InstallHint "Install Node.js 20+ and add it to PATH."
    $nodeExe = Resolve-RequiredCommand -Name "node" -InstallHint "Install Node.js 20+ and add it to PATH."

    $pythonVersion = Invoke-CheckedCommand -Name "python --version" -FilePath $script:PythonExe -Arguments @("--version")
    $nodeVersion = Invoke-CheckedCommand -Name "node --version" -FilePath $nodeExe -Arguments @("--version")
    Invoke-CheckedCommand -Name "npm --version" -FilePath $script:NpmExe -Arguments @("--version") | Out-Null

    $pythonText = ($pythonVersion.Output -join " ")
    if ($pythonText -notmatch "Python\s+(\d+)\.(\d+)") {
        throw ("Could not determine Python version from: {0}" -f $pythonText)
    }
    if ([int]$Matches[1] -lt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -lt 11)) {
        throw ("Python 3.11+ is required. Found: {0}" -f $pythonText)
    }

    $nodeText = ($nodeVersion.Output -join " ")
    if ($nodeText -notmatch "v(\d+)\.") {
        throw ("Could not determine Node.js version from: {0}" -f $nodeText)
    }
    if ([int]$Matches[1] -lt 20) {
        throw ("Node.js 20+ is required. Found: {0}" -f $nodeText)
    }
}

function Validate-ProjectStructure {
    Write-Log -Level STEP -Message "2/7 Validate project structure"
    $requiredPaths = @(
        $script:BackendDir,
        (Join-Path $script:BackendDir "requirements.txt"),
        (Join-Path $script:BackendDir "app\main.py"),
        $script:FrontendDir,
        (Join-Path $script:FrontendDir "package.json"),
        (Join-Path $script:FrontendDir "vite.config.ts"),
        (Join-Path $script:ScriptDir "logger.ps1"),
        (Join-Path $script:ScriptDir "healthcheck.ps1")
    )

    foreach ($path in $requiredPaths) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw ("Required path missing: {0}" -f $path)
        }
        Write-Log -Level OK -Message ("Present: {0}" -f $path)
    }
}

function Configure-BackendEnvironment {
    Write-Log -Level STEP -Message "3/7 Configure backend environment"
    $envFile = Join-Path $script:BackendDir ".env"
    $envExample = Join-Path $script:BackendDir ".env.example"
    $requiredOriginsValue = '["http://localhost:5173","http://127.0.0.1:5173","http://localhost:3000","http://127.0.0.1:3000","http://localhost:80","http://127.0.0.1:80"]'

    if (Test-Path -LiteralPath $envFile) {
        Write-Log -Level OK -Message "backend\.env already exists"
        $content = @(Get-Content -LiteralPath $envFile)
        $originLine = $content | Where-Object { $_ -match "^\s*ALLOWED_ORIGINS\s*=" } | Select-Object -First 1
        if (-not $originLine -or $originLine -notmatch "127\.0\.0\.1:5173") {
            $updated = $false
            for ($i = 0; $i -lt $content.Count; $i++) {
                if ($content[$i] -match "^\s*ALLOWED_ORIGINS\s*=") {
                    $content[$i] = "ALLOWED_ORIGINS={0}" -f $requiredOriginsValue
                    $updated = $true
                    break
                }
            }
            if (-not $updated) {
                $content += "ALLOWED_ORIGINS={0}" -f $requiredOriginsValue
            }
            Set-Content -LiteralPath $envFile -Value $content -Encoding ASCII
            Write-Log -Level OK -Message "Updated backend\.env CORS origins for local launcher hosts"
        }
        return
    }

    if (Test-Path -LiteralPath $envExample) {
        Copy-Item -LiteralPath $envExample -Destination $envFile -Force
        Write-Log -Level OK -Message "Created backend\.env from backend\.env.example"
        return
    }

    $lines = @(
        "APP_VERSION=1.0.0",
        "DEMO_MODE=true",
        "DEMO_CRASH_INTERVAL_SECONDS=45",
        "DEMO_HOSPITAL_UPDATE_INTERVAL_SECONDS=15",
        "BANGALORE_LAT=12.9716",
        "BANGALORE_LON=77.5946",
        ("ALLOWED_ORIGINS={0}" -f $requiredOriginsValue),
        "DATABASE_URL=sqlite:///./roadsos.db",
        "WS_HEARTBEAT_INTERVAL=30",
        "CRASH_CONFIRM_THRESHOLD=0.85",
        "CRASH_SUSPECT_THRESHOLD=0.60",
        "BLACKSPOT_RISK_THRESHOLD=65"
    )
    Set-Content -Path $envFile -Value $lines -Encoding ASCII
    Write-Log -Level OK -Message "Created default backend\.env"
}

function Import-BackendEnvironment {
    Write-Log -Level STEP -Message "Applying backend environment"
    $envFile = Join-Path $script:BackendDir ".env"
    if (-not (Test-Path -LiteralPath $envFile)) {
        throw ("Backend environment file missing: {0}" -f $envFile)
    }

    $loaded = 0
    $lines = Get-Content -LiteralPath $envFile
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#")) {
            continue
        }

        $separatorIndex = $trimmed.IndexOf("=")
        if ($separatorIndex -le 0) {
            continue
        }

        $name = $trimmed.Substring(0, $separatorIndex).Trim()
        $value = $trimmed.Substring($separatorIndex + 1).Trim()
        if ($name -match "^[A-Za-z_][A-Za-z0-9_]*$") {
            Set-Item -Path ("Env:\{0}" -f $name) -Value $value
            $loaded++
        }
    }

    Write-Log -Level OK -Message ("Applied {0} backend environment variable(s)" -f $loaded)
}

function Ensure-PythonBackend {
    Write-Log -Level STEP -Message "4/7 Prepare Python backend"
    $venvDir = Join-Path $script:BackendDir ".venv"

    if (-not (Test-Path -LiteralPath $script:VenvPython)) {
        Write-Log -Level INFO -Message "Creating Python virtual environment"
        Invoke-CheckedCommand -Name "python venv" -FilePath $script:PythonExe -Arguments @("-m", "venv", ".venv") -WorkingDirectory $script:BackendDir | Out-Null
    } else {
        Write-Log -Level OK -Message ("Virtual environment exists: {0}" -f $venvDir)
    }

    if (-not (Test-Path -LiteralPath $script:VenvPython)) {
        throw ("Virtual environment Python not found: {0}" -f $script:VenvPython)
    }

    $check = Invoke-CheckedCommand -Name "python import check" -FilePath $script:VenvPython -Arguments @("-c", "import fastapi, uvicorn, httpx, websockets") -WorkingDirectory $script:BackendDir -AllowFailure
    if ($check.ExitCode -eq 0) {
        Write-Log -Level OK -Message "Core backend packages are installed"
        return
    }

    Write-Log -Level INFO -Message "Installing backend requirements"
    Invoke-CheckedCommand -Name "pip bootstrap" -FilePath $script:VenvPython -Arguments @("-m", "ensurepip", "--upgrade") -WorkingDirectory $script:BackendDir -AllowFailure | Out-Null
    Invoke-CheckedCommand -Name "pip install requirements" -FilePath $script:VenvPython -Arguments @("-m", "pip", "install", "-r", "requirements.txt", "--default-timeout", "180", "--disable-pip-version-check") -WorkingDirectory $script:BackendDir | Out-Null
    Invoke-CheckedCommand -Name "python import verify" -FilePath $script:VenvPython -Arguments @("-c", "import fastapi, uvicorn, httpx, websockets") -WorkingDirectory $script:BackendDir | Out-Null
    Write-Log -Level OK -Message "Backend dependencies are ready"
}

function Ensure-Frontend {
    Write-Log -Level STEP -Message "5/7 Prepare frontend"
    $nodeModules = Join-Path $script:FrontendDir "node_modules"
    $viteJs = Join-Path $script:FrontendDir "node_modules\vite\bin\vite.js"
    $lockFile = Join-Path $script:FrontendDir "package-lock.json"
    $installCommand = if (Test-Path -LiteralPath $lockFile) { "ci" } else { "install" }

    if (-not (Test-Path -LiteralPath $nodeModules)) {
        Write-Log -Level INFO -Message "Installing frontend dependencies"
        Invoke-CheckedCommand -Name ("npm {0}" -f $installCommand) -FilePath $script:NpmExe -Arguments @($installCommand, "--no-fund", "--no-audit", "--legacy-peer-deps") -WorkingDirectory $script:FrontendDir | Out-Null
    } else {
        Write-Log -Level OK -Message "node_modules already exists"
    }

    if (-not (Test-Path -LiteralPath $viteJs)) {
        Write-Log -Level WARN -Message ("Vite package not found; running npm {0} again" -f $installCommand)
        Invoke-CheckedCommand -Name ("npm {0} retry" -f $installCommand) -FilePath $script:NpmExe -Arguments @($installCommand, "--no-fund", "--no-audit", "--legacy-peer-deps") -WorkingDirectory $script:FrontendDir | Out-Null
    }

    if (-not (Test-Path -LiteralPath $viteJs)) {
        throw ("Vite executable script not found: {0}" -f $viteJs)
    }

    Write-Log -Level OK -Message "Frontend dependencies are ready"
}

function Start-Backend {
    $stdout = Join-Path $script:LogDir "backend_stdout.log"
    $stderr = Join-Path $script:LogDir "backend_stderr.log"
    Remove-Item -LiteralPath $stdout, $stderr -Force -ErrorAction SilentlyContinue

    $arguments = @(
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        ([string]$script:BackendPort),
        "--log-level",
        "info"
    )

    Write-Log -Level STEP -Message ("Starting backend on {0}" -f $script:BackendUrl)
    $script:BackendProcess = Start-Process -FilePath $script:VenvPython -ArgumentList $arguments -WorkingDirectory $script:BackendDir -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
    Write-Log -Level OK -Message ("Backend process started. PID {0}" -f $script:BackendProcess.Id)
    Write-Log -Level INFO -Message ("Backend stdout: {0}" -f $stdout)
    Write-Log -Level INFO -Message ("Backend stderr: {0}" -f $stderr)
}

function Start-Frontend {
    $stdout = Join-Path $script:LogDir "frontend_stdout.log"
    $stderr = Join-Path $script:LogDir "frontend_stderr.log"
    Remove-Item -LiteralPath $stdout, $stderr -Force -ErrorAction SilentlyContinue

    $arguments = @(
        "run",
        "dev",
        "--",
        "--host",
        "127.0.0.1",
        "--port",
        ([string]$script:FrontendPort),
        "--strictPort"
    )

    Write-Log -Level STEP -Message ("Starting frontend on {0}" -f $script:FrontendUrl)
    $script:FrontendProcess = Start-Process -FilePath $script:NpmExe -ArgumentList $arguments -WorkingDirectory $script:FrontendDir -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
    Write-Log -Level OK -Message ("Frontend process started. PID {0}" -f $script:FrontendProcess.Id)
    Write-Log -Level INFO -Message ("Frontend stdout: {0}" -f $stdout)
    Write-Log -Level INFO -Message ("Frontend stderr: {0}" -f $stderr)
}

function Assert-ProcessStillRunning {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process
    )

    Start-Sleep -Seconds 1
    $fresh = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
    if (-not $fresh) {
        throw ("{0} process exited immediately. PID was {1}" -f $Name, $Process.Id)
    }
}

function Start-Services {
    Write-Log -Level STEP -Message "6/7 Start services"
    Clear-RoadSoSPorts

    Start-Backend
    Assert-ProcessStillRunning -Name "Backend" -Process $script:BackendProcess

    $retries = if ($DebugMode) { 60 } else { 45 }
    $backendHealth = Test-BackendHealth -BaseUrl $script:BackendUrl -MaxRetries $retries -DelaySeconds 2
    if (-not $backendHealth.Success) {
        throw "Backend failed readiness check"
    }

    Start-Frontend
    Assert-ProcessStillRunning -Name "Frontend" -Process $script:FrontendProcess

    $frontendHealth = Test-FrontendHealth -BaseUrl $script:FrontendUrl -MaxRetries $retries -DelaySeconds 2
    if (-not $frontendHealth.Success) {
        throw "Frontend failed readiness check"
    }
}

function Final-Verification {
    Write-Log -Level STEP -Message "7/7 Final verification"
    $backend = Test-HttpEndpoint -Url ("{0}/health" -f $script:BackendUrl) -TimeoutSeconds 5
    if (-not $backend.Success) {
        throw "Backend final verification failed"
    }

    $frontend = Test-HttpEndpoint -Url ("{0}/" -f $script:FrontendUrl) -TimeoutSeconds 5
    if (-not $frontend.Success) {
        throw "Frontend final verification failed"
    }

    Write-Log -Level OK -Message ("Backend health: {0}/health" -f $script:BackendUrl)
    Write-Log -Level OK -Message ("Frontend: {0}/" -f $script:FrontendUrl)
}

function Open-RoadSoSBrowser {
    Write-Log -Level INFO -Message "Opening browser"
    Start-Process -FilePath $script:FrontendUrl | Out-Null
}

function Stop-StartedProcessesOnFailure {
    foreach ($process in @($script:FrontendProcess, $script:BackendProcess)) {
        if ($process -and -not $process.HasExited) {
            try {
                Write-Log -Level WARN -Message ("Stopping started process PID {0}" -f $process.Id)
                Stop-Process -Id $process.Id -Force -ErrorAction Stop
            } catch {
                Write-Log -Level WARN -Message ("Could not stop PID {0}: {1}" -f $process.Id, $_.Exception.Message)
            }
        }
    }
}

function Main {
    Initialize-Logger -LogDir $script:LogDir -LogPrefix $LogPrefix -DebugEnabled:$DebugMode | Out-Null
    Show-Banner

    Write-Log -Level INFO -Message ("Root: {0}" -f $script:RootDir)
    Write-Log -Level INFO -Message ("PowerShell: {0}" -f $PSVersionTable.PSVersion.ToString())

    Validate-Environment
    Validate-ProjectStructure
    Configure-BackendEnvironment
    Import-BackendEnvironment
    Ensure-PythonBackend
    Ensure-Frontend
    Start-Services
    Final-Verification
    Open-RoadSoSBrowser

    Write-Log -Level OK -Message "RoadSoS is live"
    Write-Log -Level OK -Message ("Frontend: {0}/" -f $script:FrontendUrl)
    Write-Log -Level OK -Message ("Backend: {0}/health" -f $script:BackendUrl)
    Write-Log -Level OK -Message ("API docs: {0}/api/docs" -f $script:BackendUrl)
    Write-Log -Level INFO -Message ("Log file: {0}" -f (Get-LogFilePath))
    $script:ExitCode = 0
}

try {
    Main
} catch {
    Write-Log -Level ERROR -Message ("Startup failed: {0}" -f $_.Exception.Message)
    Write-Log -Level ERROR -Message ("Failing location: {0}" -f $_.InvocationInfo.PositionMessage)
    if ($_.ScriptStackTrace) {
        Write-Log -Level DEBUG -Message ("Stack trace: {0}" -f $_.ScriptStackTrace)
    }
    Stop-StartedProcessesOnFailure
    $script:ExitCode = 1
} finally {
    Close-Logger
}

if ($DebugMode -or $script:ExitCode -ne 0) {
    Write-Host ""
    Read-Host "Press Enter to exit" | Out-Null
}

exit $script:ExitCode
