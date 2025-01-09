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

import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { DeviceService } from './device.service';
import { HttpApiClient } from '../common/http/http';
import { CommandService } from '../command/command.service';
import { environment } from '../../../environments/environment';
import { Device, DeviceList } from '@samplers/device';
import { provideHttpClient } from '@angular/common/http';
import { DeviceFrame, DeviceV2, SENSOR_SIZE } from './device';
import { firstValueFrom } from 'rxjs';
import { SMALLEST_VALID_PNG } from '@samplers/qr';
import { Point2D } from '../drawing/drawing';
import { TIME_BETWEEN_FRAMES } from './device-visualizer/device-visualizer.component';

export class MockCommandService {
  executeCommandV2 = jest.fn();
}

describe('DeviceService', () => {
  let service: DeviceService;
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
        `${environment.apiV2Url}/devices?limit=500`,
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
        `${environment.apiV2Url}/devices?device_ids=1,2`,
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockDevices);

      await deferred;
    });
  });

  describe('deleteDevice', () => {
    it('should delete a device', async () => {
      const device = Device.sampleLocal(Device.sample(), 12345);
      const list = DeviceList.sampleLocal();

      service.deleteDevice(device);

      const deleteRequest = httpMock.expectOne(
        `${environment.apiV2Url}/devices/12345`,
      );
      expect(deleteRequest.request.method).toBe('DELETE');
      deleteRequest.flush(null);
      await new Promise(process.nextTick);

      const getRequest = httpMock.expectOne(
        `${environment.apiV2Url}/devices?limit=500`,
      );
      expect(getRequest.request.method).toBe('GET');
      getRequest.flush(list);

      await expect(firstValueFrom(service.devices$)).resolves.toEqual(
        list.devices,
      );
    });
  });

  describe('getDeviceNextImage', () => {
    it('should return a data uri image if device is reachable', async () => {
      const device = Device.sampleLocal();

      commandService.executeCommandV2.mockResolvedValue({
        result: 'SUCCESS',
        command_response: {
          image: SMALLEST_VALID_PNG,
        },
      });

      const img = await service.getDeviceNextImage(device);

      expect(img).toContain(SMALLEST_VALID_PNG);
      expect(commandService.executeCommandV2).toHaveBeenCalledWith(
        device.port.toString(),
        '$system',
        expect.objectContaining({ command_name: 'direct_get_image' }),
      );
    });

    it('should return an error if command results in error', async () => {
      const device = Device.sampleLocal();

      commandService.executeCommandV2.mockResolvedValue({ result: 'ERROR' });

      expect(service.getDeviceNextImage(device)).rejects.toThrow();
    });
  });

  describe('deviceSelected$', () => {
    it('should emit the correct device when setSelectedDevice is called with a valid device', (done) => {
      const sampleDevice = Device.sample();

      service.deviceSelected$.subscribe((device) => {
        expect(device).toEqual(sampleDevice);
        done();
      });

      service.setSelectedDevice(sampleDevice);
    });

    it('should not emit when setSelectedDevice is called with null', () => {
      const mockFn = jest.fn();
      service.deviceSelected$.subscribe(mockFn);

      service.setSelectedDevice(<DeviceV2>(<unknown>null));

      expect(mockFn).not.toHaveBeenCalled();
    });

    it('should emit only the last device to new subscribers after multiple calls to setSelectedDevice', (done) => {
      const firstDevice = Device.sample();
      const secondDevice = Device.sample();

      service.setSelectedDevice(firstDevice);
      service.setSelectedDevice(secondDevice);

      service.deviceSelected$.subscribe((device) => {
        expect(device).toEqual(secondDevice);

        // Test a new subscription again
        const newMockFn = jest.fn();
        service.deviceSelected$.subscribe(newMockFn);
        expect(newMockFn).toHaveBeenCalledWith(secondDevice);
        done();
      });
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
        `${environment.apiV2Url}/devices?limit=500`,
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
        `${environment.apiV2Url}/devices?limit=500`,
      );
      expect(req.request.method).toBe('GET');
      req.flush('retrieval error', { status: 500, statusText: 'Server Error' });

      await deferred;
    });
  });

  describe('createDevice', () => {
    it('should post to /devices on creation', async () => {
      const list = DeviceList.sampleLocal();
      const device_name = 'My device';
      const mqtt_port = 12345;

      expect(service.createDevice(device_name, mqtt_port)).resolves.toBeFalsy();

      const req = httpMock.expectOne(`${environment.apiV2Url}/devices`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toHaveProperty('device_name', device_name);
      expect(req.request.body).toHaveProperty('mqtt_port', mqtt_port);
      req.flush('');
      await new Promise(process.nextTick);

      const getRequest = httpMock.expectOne(
        `${environment.apiV2Url}/devices?limit=500`,
      );
      expect(getRequest.request.method).toBe('GET');
      getRequest.flush(list);

      await expect(firstValueFrom(service.devices$)).resolves.toEqual(
        list.devices,
      );
    });
  });

  describe('getDeviceStream', () => {
    it('should push device image to the stream when getPreviewImageV2 is successful', (done) => {
      // Mock the internal HTTP call within getDeviceNextImage
      const device = Device.sampleLocal();
      commandService.executeCommandV2.mockReturnValue({
        result: 'SUCCESS',
        command_response: {
          image: SMALLEST_VALID_PNG,
        },
      });

      const { stream, stopStream } = service.getDeviceStream(
        device,
        new Point2D(0, 0),
        SENSOR_SIZE,
        TIME_BETWEEN_FRAMES,
      );

      stream.subscribe((frame) => {
        expect((frame as DeviceFrame).image).toContain(SMALLEST_VALID_PNG);
        stopStream();
        done();
      });
    });

    it('should push an error to the stream when getPreviewImageV2 fails', (done) => {
      // Mock the internal HTTP call to simulate failure
      const device = Device.sampleLocal();
      commandService.executeCommandV2.mockResolvedValue({ result: 'ERROR' });

      const { stream, stopStream } = service.getDeviceStream(
        device,
        new Point2D(0, 0),
        SENSOR_SIZE,
        TIME_BETWEEN_FRAMES,
      );

      stream.subscribe((frame) => {
        expect(frame).toBeInstanceOf(Error);
        stopStream();
        done();
      });
    });

    it('should stop calling getPreviewImageV2 after stopStream is called', async () => {
      const device = Device.sampleLocal();
      commandService.executeCommandV2.mockReturnValue({
        result: 'SUCCESS',
        command_response: {
          image: SMALLEST_VALID_PNG,
        },
      });

      const { stream, stopStream } = service.getDeviceStream(
        device,
        new Point2D(0, 0),
        SENSOR_SIZE,
        TIME_BETWEEN_FRAMES,
      );

      stopStream();

      // Should only be called once before stopStream
      expect(commandService.executeCommandV2).toHaveBeenCalledTimes(1);
    });
  });
});
