# create_venv.ps1
# Removes existing .venv directory, creates a new Python virtualenv at .venv,
# upgrades pip, wheel, setuptools, then installs a list of packages.
# Usage:
#   .\tools\create_venv.ps1                # installs default packages (requirements.txt)
#   .\tools\create_venv.ps1 pkg1 pkg2 ...  # installs specified packages

$ErrorActionPreference = "Stop"

$workDir = (Get-Location).Path
$venvDir = Join-Path $workDir ".venv"
$requirementsPath = Join-Path $workDir "requirements.txt"

function Test-IsAdministrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (Test-IsAdministrator) {
    Write-Error "Don't run this script as Administrator. Exiting."
    exit 1
}

Write-Host "This will remove '$venvDir' if it exists, then create a new venv."
Write-Host "Proceeding without prompt (non-interactive mode)."

if (Test-Path $venvDir) {
    Write-Host "Removing existing venv at $venvDir"
    Remove-Item -Recurse -Force $venvDir
}

Write-Host "Creating venv at $venvDir"
python -m venv $venvDir

Write-Host "Activating venv"
$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
. $activateScript

if ($args.Count -gt 0) {
    Write-Host "Installing packages: $($args -join ' ')"
    pip install @args
}
else {
    Write-Host "Installing packages from requirements.txt"
    if (-not (Test-Path $requirementsPath)) {
        Write-Error "requirements.txt not found at $requirementsPath"
        exit 1
    }
    pip install -r $requirementsPath
}

Write-Host "Installation complete. To activate the venv, run:"
Write-Host "  $activateScript"

exit 0