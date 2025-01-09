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

Run-Privileged $MyInvocation.MyCommand.Source $TargetPath

function Grant-ConnectionsInFirewall([string]$TargetPath)
{
	# What follows must be run as Administrator
    if (-not $(Check-Privilege)) {
        Exit
    }

    # Validate that the executable exists
    if (-not (Test-Path $TargetPath)) {
        Write-Error "The specified executable does not exist: $TargetPath"
        exit
    }

    # Define the firewall rule name
    $ruleName = "Local Console: Allow Inbound for " + (Split-Path $TargetPath -Leaf)

    # Check if the rule already exists
    $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

    if ($existingRule) {
        Write-LogMessage "Firewall rule already exists: $ruleName"
    } else {
        # Create the new firewall rule
        New-NetFirewallRule `
            -DisplayName $ruleName `
            -Direction Inbound `
            -Program $TargetPath `
            -Action Allow `
            -Profile Any
        Write-LogMessage "Firewall rule created: $ruleName"
    }
}

Grant-ConnectionsInFirewall $TargetPath
