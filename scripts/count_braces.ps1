$c = Get-Content "c:\Eshant_Sonhar\Road Safety Hackathon\scripts\launcher.ps1"
$open = 0
$close = 0
foreach ($l in $c) {
    $open += [regex]::Matches($l, '{').Count
    $close += [regex]::Matches($l, '}').Count
}
Write-Host "Open braces: $open"
Write-Host "Close braces: $close"
if ($open -eq $close) {
    Write-Host "Balanced!" -ForegroundColor Green
} else {
    Write-Host "MISMATCH: $($open - $close) unclosed" -ForegroundColor Red
}