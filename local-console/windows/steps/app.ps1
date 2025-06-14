# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
Param (
	[String] $InstallPath,
	[String] $WheelPath,
    [String] $TranscriptPath
)
$DoRedirect = -not [string]::IsNullOrWhiteSpace($TranscriptPath)

$rootPath = Split-Path -parent $MyInvocation.MyCommand.Path | Split-Path -parent
$utils = Join-Path $rootPath "utils.ps1"
. $utils

# URLs of binary dependencies
$DepURLFlatc = 'https://github.com/google/flatbuffers/releases/download/v24.3.25/Windows.flatc.binary.zip'
$DepURLWabt = 'https://github.com/WebAssembly/wabt/releases/download/1.0.36/wabt-1.0.36-windows.tar.gz'

function Main
{
    if ($DoRedirect) {
        Start-Transcript -Path "$TranscriptPath" -Append
    }

    Refresh-Path
    Create-AppDataDirectory -Path $InstallPath
    $virtualenvDir = Join-Path $InstallPath "virtualenv"
    Create-PythonEnvWithExecutable -VirtualenvDir $virtualenvDir -WheelPath $WheelPath

    $binPath = Join-Path $VirtualenvDir "Scripts"
    Get-FlatcBinary -ScriptsDir $binPath
    Get-WasmValidateBinary -ScriptsDir $binPath
}

function Create-PythonEnvWithExecutable([string]$VirtualenvDir, [string]$WheelPath)
{
    # Check if the directory already exists
    if (Test-Path -Path $VirtualenvDir -PathType Container) {
        Write-LogMessage "Virtualenv parent folder already exists at $VirtualenvDir"
    } else {
        # Attempt to create the directory
        try {
            New-Item -Path $VirtualenvDir -ItemType Directory | Out-Null
            Write-LogMessage "Virtualenv parent created successfully: $VirtualenvDir"
        } catch {
            Write-LogMessage "Failed to create parent: $_"
        }
    }

    $PythonAtVenv = Join-Path $VirtualenvDir "Scripts" `
                  | Join-Path -ChildPath "python.exe"
    if (Test-Path $PythonAtVenv -PathType Leaf) {
        Write-LogMessage "Virtual environment is already present."
    } else {
        Write-LogMessage "Virtual environment will be created in $VirtualenvDir"
        python -m venv $VirtualenvDir
        Write-LogMessage "Virtual environment created."
    }

    $UseWheel = -not [string]::IsNullOrWhiteSpace($WheelPath)
    if ($UseWheel) {
        & $PythonAtVenv -m pip install "$WheelPath"
    }
    else {
        # Install from the repo sources
        $repoPath = Split-Path -parent $Script:MyInvocation.MyCommand.Path `
                  | Split-Path -parent `
                  | Split-Path -parent
        & $PythonAtVenv -m pip install "$repoPath"
    }

    if ($LASTEXITCODE -eq 0) {
        Write-LogMessage "Local Console has been installed."
    } else {
        Write-Error "Error activating the virtualenv"
        Exit 1
    }

    Write-LogMessage "Virtual environment has been updated."
}

function Get-FlatcBinary([string]$ScriptsDir)
{
    $flatcPath = Join-Path $ScriptsDir "flatc.exe"

    if (Test-Path $flatcPath -PathType Leaf) {
        Write-LogMessage "Flatc already installed at $ScriptsDir"
        return
    }

    # Download the zip file
    $zipPath = Join-Path $env:TEMP "tempExecutable.zip"

    # Initialize a flag to indicate the download success status
    $downloadSuccessful = $false
    # Loop until the download is successful
    while (-not $downloadSuccessful) {
        try {
            $ProgressPreference = 'SilentlyContinue'
            Invoke-WebRequest -Uri $DepURLFlatc -OutFile $zipPath -Verbose:$false
            $downloadSuccessful = $true
        } catch {
            $statusCode = $_.Exception.Response.StatusCode.value__
            Write-Output "Download failed (got code $statusCode). Retrying..."
            Start-Sleep -Seconds 5
        }
    }
    Write-LogMessage "Flatc Zipball downloaded."


    # Initialize a flag to indicate the download success status
    $unpackSuccessful = $false
    # Loop until the download is successful
    while (-not $unpackSuccessful) {
        try {
            $ProgressPreference = 'SilentlyContinue'
            # Unpack the zip file directly into the virtual environment's Scripts/ directory
            Expand-Archive -Path $zipPath -DestinationPath $ScriptsDir -Force -Verbose:$false
            Write-LogMessage "Flatc Executable unpacked into $ScriptsDir"
            $unpackSuccessful = $true
        } catch {
            Write-Output "Unpack failed (got $($_.Exception)). Retrying..."
            Start-Sleep -Seconds 2
        }
    }

    # Cleanup the downloaded zip file
    Remove-Item -Path $zipPath
}

function Get-WasmValidateBinary([string]$ScriptsDir)
{
    $wasmValidatePath = Join-Path $ScriptsDir "wasm-validate.exe"

    if (Test-Path $wasmValidatePath -PathType Leaf) {
        Write-LogMessage "wasm-validate already installed at $ScriptsDir"
        return
    }

    # Download the tarball file
    $tarballPath = Join-Path $env:TEMP "wabt-1.0.36-windows.tar.gz"

    # Initialize a flag to indicate the download success status
    $downloadSuccessful = Test-Path $tarballPath -PathType Leaf
    # Loop until the download is successful
    while (-not $downloadSuccessful) {
        try {
            $ProgressPreference = 'SilentlyContinue'
            Invoke-WebRequest -Uri $DepURLWabt -OutFile $tarballPath -Verbose:$false
            $downloadSuccessful = $true
        } catch {
            $statusCode = $_.Exception.Response.StatusCode.value__
            Write-Output "Download failed (got code $statusCode). Retrying..."
            Start-Sleep -Seconds 5
        }
    }
    Write-LogMessage "WABT tarball downloaded."

    # Initialize a flag to indicate the download success status
    $unpackSuccessful = $false
    # Loop until the download is successful
    while (-not $unpackSuccessful) {
        try {
            $ProgressPreference = 'SilentlyContinue'
            # Unpack the tarball file directly into the virtual environment's Scripts/ directory
            python -c "import tarfile; from pathlib import Path; pkg = tarfile.open(r'$tarballPath'); wval = next(t for t in pkg if 'wasm-validate.exe' in t.name.lower()); target = Path(r'$wasmValidatePath'); target.write_bytes(pkg.extractfile(wval).read())"
            Write-LogMessage "wasm-validate Executable unpacked into $ScriptsDir"
            $unpackSuccessful = $true
        } catch {
            Write-Output "Unpack failed (got $($_.Exception)). Retrying..."
            Start-Sleep -Seconds 2
        }
    }

    # Cleanup the downloaded zip file
    Remove-Item -Path $tarballPath
}

function Create-AppDataDirectory([string]$Path)
{
    # Check if the directory already exists
    if (Test-Path -Path $Path) {
        Write-LogMessage "Directory already exists: $Path"
    } else {
        # Attempt to create the directory
        try {
            New-Item -Path $Path -ItemType Directory | Out-Null
            Write-LogMessage "Directory created successfully: $Path"
        } catch {
            Write-LogMessage "Failed to create directory: $_"
        }
    }
}

Main
