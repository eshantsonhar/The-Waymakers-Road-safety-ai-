# ============================================================================
# RoadSoS - Logger
# PowerShell 5.1 compatible logging helpers.
# ============================================================================

$script:RoadSoSLogFilePath = $null
$script:RoadSoSDebugEnabled = $false
$script:RoadSoSLogColors = @{
    INFO  = 'Cyan'
    OK    = 'Green'
    WARN  = 'Yellow'
    ERROR = 'Red'
    STEP  = 'Magenta'
    DEBUG = 'DarkGray'
    WAIT  = 'DarkYellow'
}

function Initialize-Logger {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogDir,

        [string]$LogPrefix = "startup",

        [switch]$DebugEnabled
    )

    if (-not (Test-Path -LiteralPath $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }

    $script:RoadSoSDebugEnabled = [bool]$DebugEnabled
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $script:RoadSoSLogFilePath = Join-Path $LogDir ("{0}_{1}.log" -f $LogPrefix, $timestamp)
    New-Item -ItemType File -Path $script:RoadSoSLogFilePath -Force | Out-Null

    Write-Log -Level INFO -Message ("Log file: {0}" -f $script:RoadSoSLogFilePath)
    return $script:RoadSoSLogFilePath
}

function Write-Log {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('INFO', 'OK', 'WARN', 'ERROR', 'STEP', 'DEBUG', 'WAIT')]
        [string]$Level,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Message
    )

    if ($Level -eq 'DEBUG' -and -not $script:RoadSoSDebugEnabled) {
        return
    }

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'
    $line = "[{0}] [{1}] {2}" -f $timestamp, $Level, $Message
    $color = $script:RoadSoSLogColors[$Level]

    if ($color) {
        Write-Host $line -ForegroundColor $color
    } else {
        Write-Host $line
    }

    if ($script:RoadSoSLogFilePath) {
        Add-Content -Path $script:RoadSoSLogFilePath -Value $line -Encoding UTF8
    }
}

function Write-CommandResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [int]$ExitCode,

        [object[]]$Output
    )

    Write-Log -Level DEBUG -Message ("Command '{0}' exited with code {1}" -f $Name, $ExitCode)
    if ($Output) {
        foreach ($item in $Output) {
            if ($null -ne $item) {
                Write-Log -Level DEBUG -Message ("{0}: {1}" -f $Name, ($item.ToString()))
            }
        }
    }
}

function Get-LogFilePath {
    return $script:RoadSoSLogFilePath
}

function Close-Logger {
    if ($script:RoadSoSLogFilePath) {
        Write-Log -Level INFO -Message "Log session ended"
    }
}
