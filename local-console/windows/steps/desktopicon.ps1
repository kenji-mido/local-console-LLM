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
	[String] $TargetPath
)

$rootPath = Split-Path -parent $MyInvocation.MyCommand.Path | Split-Path -parent
$utils = Join-Path $rootPath "utils.ps1"
. $utils

function Create-DesktopShortcut([string]$TargetPath)
{
    $WshShell = New-Object -comObject WScript.Shell
    $DestinationPath = Join-Path $WshShell.SpecialFolders("Desktop") "Local Console.lnk"

    # If icon already exists, just remove it so that we make sure it is
    # kept up to date since recreating has zero cost.
    if (Test-Path $DestinationPath -PathType Leaf) {
        Remove-Item -Path $DestinationPath
    }
    Write-LogMessage "Creating icon for $TargetPath"

    $SourceExe = Resolve-Path $TargetPath

    $Shortcut = $WshShell.CreateShortcut($DestinationPath)
    $Shortcut.TargetPath = $SourceExe.Path
    $Shortcut.WorkingDirectory = $env:HOME
    $Shortcut.Description = "Starts Local Console"
    $Shortcut.Save()

    Write-LogMessage "Created desktop shortcut at: $DestinationPath"
}

Create-DesktopShortcut $TargetPath
