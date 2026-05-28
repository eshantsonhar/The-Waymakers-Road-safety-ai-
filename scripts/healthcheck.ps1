# ============================================================================
# RoadSoS - Health Checks
# Import-safe functions for backend/frontend readiness checks.
# ============================================================================

function Test-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [int]$TimeoutSeconds = 3
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSeconds -ErrorAction Stop
        return @{
            Success    = ($response.StatusCode -eq 200)
            StatusCode = $response.StatusCode
            Content    = $response.Content
            Error      = $null
        }
    } catch {
        return @{
            Success    = $false
            StatusCode = $null
            Content    = $null
            Error      = $_.Exception.Message
        }
    }
}

function Wait-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Url,

        [int]$MaxRetries = 30,

        [int]$DelaySeconds = 2,

        [int]$TimeoutSeconds = 3
    )

    $startedAt = Get-Date
    Write-Log -Level WAIT -Message ("Waiting for {0}: {1}" -f $Name, $Url)

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        $result = Test-HttpEndpoint -Url $Url -TimeoutSeconds $TimeoutSeconds
        if ($result.Success) {
            $elapsed = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 1)
            Write-Log -Level OK -Message ("{0} is ready after {1}s ({2}/{3})" -f $Name, $elapsed, $attempt, $MaxRetries)
            return @{
                Success    = $true
                Attempts   = $attempt
                Seconds    = $elapsed
                StatusCode = $result.StatusCode
                Content    = $result.Content
                Error      = $null
            }
        }

        if (($attempt % 5) -eq 0) {
            Write-Log -Level WAIT -Message ("{0} not ready yet ({1}/{2}): {3}" -f $Name, $attempt, $MaxRetries, $result.Error)
        }

        if ($attempt -lt $MaxRetries) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    $elapsedFailed = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 1)
    Write-Log -Level ERROR -Message ("{0} did not become ready after {1}s" -f $Name, $elapsedFailed)
    return @{
        Success    = $false
        Attempts   = $MaxRetries
        Seconds    = $elapsedFailed
        StatusCode = $null
        Content    = $null
        Error      = "Timed out"
    }
}

function Test-BackendHealth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseUrl,

        [int]$MaxRetries = 30,

        [int]$DelaySeconds = 2
    )

    return Wait-HttpEndpoint -Name "backend" -Url ("{0}/health" -f $BaseUrl) -MaxRetries $MaxRetries -DelaySeconds $DelaySeconds
}

function Test-FrontendHealth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseUrl,

        [int]$MaxRetries = 30,

        [int]$DelaySeconds = 2
    )

    return Wait-HttpEndpoint -Name "frontend" -Url ("{0}/" -f $BaseUrl) -MaxRetries $MaxRetries -DelaySeconds $DelaySeconds
}

function Test-RoadSoSHealth {
    param(
        [string]$BackendUrl = "http://127.0.0.1:8000",
        [string]$FrontendUrl = "http://127.0.0.1:5173",
        [int]$Retries = 30,
        [int]$DelaySeconds = 2
    )

    $backend = Test-BackendHealth -BaseUrl $BackendUrl -MaxRetries $Retries -DelaySeconds $DelaySeconds
    $frontend = Test-FrontendHealth -BaseUrl $FrontendUrl -MaxRetries $Retries -DelaySeconds $DelaySeconds

    return @{
        Success  = ($backend.Success -and $frontend.Success)
        Backend  = $backend
        Frontend = $frontend
    }
}
