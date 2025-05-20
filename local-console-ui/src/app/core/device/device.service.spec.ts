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

import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Device, DeviceList } from '@samplers/device';
import { firstValueFrom } from 'rxjs';
import { CommandService } from '../command/command.service';
import { EnvService } from '../common/environment.service';
import { HttpApiClient } from '../common/http/http';
import { DeviceService } from './device.service';

export class MockCommandService {
  executeSysAppCommand = jest.fn();
}

describe('DeviceService', () => {
  let service: DeviceService;
  let envService: EnvService;
  let httpMock: HttpTestingController;
  let commandService: MockCommandService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        DeviceService,
        { provide: CommandService, useClass: MockCommandService },
        { provide: HttpApiClient, useClass: HttpApiClient },
        provideHttpClient(),
        provideHttpClientTesting(), // Mock actual HTTP requests
      ],
    });
    service = TestBed.inject(DeviceService);
    envService = TestBed.inject(EnvService);
    httpMock = TestBed.inject(HttpTestingController);
    commandService = TestBed.inject(
      CommandService,
    ) as unknown as MockCommandService;

    //Flush constructor side-effects
  });

  afterEach(() => {
    httpMock.verify(); // Verify that no unmatched requests are outstanding.
  });

  describe('getDevicesV2', () => {
    it('should fetch devices without IDs', async () => {
      const mockDevices = DeviceList.sample();

      const deferred = service.getDevicesV2().then((response) => {
        expect(response).toEqual(mockDevices);
      });

      const req = httpMock.expectOne(
        `${envService.getApiUrl()}/devices?limit=500`,
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockDevices);

      await deferred;
    });

    it('should fetch devices with IDs', async () => {
      const mockDevices = DeviceList.sample();
      const ids = ['1', '2'];

      const deferred = service.getDevicesV2(ids).then((response) => {
        expect(response).toEqual(mockDevices);
      });

      const req = httpMock.expectOne(
        `${envService.getApiUrl()}/devices?device_ids=1,2`,
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockDevices);

      await deferred;
    });
  });

  describe('deleteDevice', () => {
    it('should delete a device', async () => {
      const device = Device.sample({
        device_name: 'device_12345',
        device_id: '12345',
      });
      const list = DeviceList.sample();

      service.deleteDevice(device);

      const deleteRequest = httpMock.expectOne(
        `${envService.getApiUrl()}/devices/12345`,
      );
      expect(deleteRequest.request.method).toBe('DELETE');
      deleteRequest.flush(null);
      await new Promise(process.nextTick);

      const getRequest = httpMock.expectOne(
        `${envService.getApiUrl()}/devices?limit=500`,
      );
      expect(getRequest.request.method).toBe('GET');
      getRequest.flush(list);

      await expect(firstValueFrom(service.devices$)).resolves.toEqual(
        list.devices,
      );
    });
  });

  describe('updateDevices', () => {
    it('should load devices and emit them through devices$', (done) => {
      const mockDevices = DeviceList.sample();

      service.devices$.subscribe((devices) => {
        expect(devices).toEqual(mockDevices.devices);
        done();
      });

      service.loadDevices();

      const req = httpMock.expectOne(
        `${envService.getApiUrl()}/devices?limit=500`,
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockDevices);
    });

    it('should send no device list in case of failure', async () => {
      service.devices$.subscribe((devices) => {
        fail('Should not send new device list');
      });

      const deferred = service.loadDevices();

      const req = httpMock.expectOne(
        `${envService.getApiUrl()}/devices?limit=500`,
      );
      expect(req.request.method).toBe('GET');
      req.flush('retrieval error', { status: 500, statusText: 'Server Error' });

      await deferred;
    });
  });

  describe('createDevice', () => {
    it('should post to /devices on creation', async () => {
      const list = DeviceList.sample();
      const device_name = 'My device';
      const mqtt_port = 12345;

      expect(service.createDevice(device_name, mqtt_port)).resolves.toBeFalsy();

      const req = httpMock.expectOne(`${envService.getApiUrl()}/devices`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toHaveProperty('device_name', device_name);
      expect(req.request.body).toHaveProperty('id', mqtt_port);
      req.flush('');
      await new Promise(process.nextTick);

      const getRequest = httpMock.expectOne(
        `${envService.getApiUrl()}/devices?limit=500`,
      );
      expect(getRequest.request.method).toBe('GET');
      getRequest.flush(list);

      await expect(firstValueFrom(service.devices$)).resolves.toEqual(
        list.devices,
      );
    });
  });
});
