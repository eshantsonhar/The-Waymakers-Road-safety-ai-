$errors = $null
$file = Join-Path (Split-Path -Parent $PSCommandPath) "launcher.ps1"
$null = [System.Management.Automation.Language.Parser]::ParseFile($file, [ref]$null, [ref]$errors)
if ($errors.Count -gt 0) {
    Write-Host "PARSE ERRORS: $($errors.Count)" -ForegroundColor Red
    foreach ($err in $errors) {
        Write-Host "  Line $($err.Extent.StartLine): $($err.Message)" -ForegroundColor Red
    }
    exit 1
} else {
    Write-Host "NO PARSE ERRORS - script is VALID" -ForegroundColor Green
    exit 0
}