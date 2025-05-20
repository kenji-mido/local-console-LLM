/**
 * Copyright 2024 Sony Semiconductor Solutions Corp.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import { Routes } from '@angular/router';
import { ROUTER_LINKS } from './core/config/routes';
import { DataHubScreen } from './layout/pages/data-hub/data-hub.screen';
import { DeploymentHubScreen } from './layout/pages/deployment-hub/deployment-hub.screen';
import { DeviceManagementScreen } from './layout/pages/device-management/device-management.screen';
import { LoadingScreen } from './layout/pages/loader/loading.screen';
import { ProvisioningScreen } from './layout/pages/provisioning-hub/provisioning.screen';

export const routes: Routes = [
  { path: '', redirectTo: ROUTER_LINKS.LOADER, pathMatch: 'full' },
  {
    path: ROUTER_LINKS.LOADER,
    component: LoadingScreen,
  },
  {
    path: ROUTER_LINKS.PROVISIONING_HUB,
    component: ProvisioningScreen,
  },
  {
    path: ROUTER_LINKS.DEPLOYMENT_HUB,
    component: DeploymentHubScreen,
  },
  {
    path: ROUTER_LINKS.DATA_HUB,
    component: DataHubScreen,
  },
  {
    path: ROUTER_LINKS.DEVICE_MANAGEMENT,
    component: DeviceManagementScreen,
  },
];
