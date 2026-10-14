$ErrorActionPreference = 'Stop'
$ClinicFlowRoot = Split-Path -Parent $PSScriptRoot
$ClinicFlowEnvPath = Join-Path $ClinicFlowRoot '.env'
if (Test-Path -LiteralPath $ClinicFlowEnvPath) {
    foreach ($ClinicFlowLine in Get-Content -LiteralPath $ClinicFlowEnvPath) {
        if ($ClinicFlowLine -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') {
            $ClinicFlowKey = $Matches[1]
            $ClinicFlowValue = $Matches[2].Trim()
            if ($ClinicFlowValue.Length -ge 2 -and (($ClinicFlowValue.StartsWith('"') -and $ClinicFlowValue.EndsWith('"')) -or ($ClinicFlowValue.StartsWith("'") -and $ClinicFlowValue.EndsWith("'")))) {
                $ClinicFlowValue = $ClinicFlowValue.Substring(1, $ClinicFlowValue.Length - 2)
            }
            # Explicit shell values take precedence, including CI settings.
            if (-not [Environment]::GetEnvironmentVariable($ClinicFlowKey, 'Process')) {
                [Environment]::SetEnvironmentVariable($ClinicFlowKey, $ClinicFlowValue, 'Process')
            }
        }
    }
}

