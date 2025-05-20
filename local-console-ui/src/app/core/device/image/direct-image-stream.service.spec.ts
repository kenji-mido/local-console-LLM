/**
 * Copyright 2025 Sony Semiconductor Solutions Corp.
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
import { CommandService } from '@app/core/command/command.service';
import { Point2D } from '@app/core/drawing/drawing';
import { ExtendedMode, Mode } from '@app/core/inference/inference';
import { SMALLEST_VALID_PNG } from '@samplers/qr';
import { DeviceFrame } from '../device';
import { DeviceService } from '../device.service';
import { DirectImageStreamService } from './direct-image-stream.service';

class MockDeviceService implements Partial<DeviceService> {
  setLastKnownRoiCache = jest.fn();
  getLastKnownRoiCache = jest.fn();
}

class MockCommandService implements Partial<CommandService> {
  executeSysAppCommand = jest.fn();
}

describe('DirectImageStreamService', () => {
  let service: DirectImageStreamService;
  let deviceService: MockDeviceService;
  let commandService: MockCommandService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        { provide: DeviceService, useClass: MockDeviceService },
        { provide: CommandService, useClass: MockCommandService },
        DirectImageStreamService,
      ],
    });

    service = TestBed.inject(DirectImageStreamService);
    deviceService = TestBed.inject(
      DeviceService,
    ) as unknown as MockDeviceService;
    commandService = TestBed.inject(
      CommandService,
    ) as unknown as MockCommandService;
  });

  it('calls setLastKnownRoiCache on init', async () => {
    await service.init(
      'dev1',
      new Point2D(1, 2),
      new Point2D(3, 4),
      Mode.ImageOnly,
    );
    expect(deviceService.setLastKnownRoiCache).toHaveBeenCalledWith('dev1', {
      offset: { x: 1, y: 2 },
      size: { x: 3, y: 4 },
    });
  });

  it('returns a DeviceFrame if response is valid', async () => {
    deviceService.getLastKnownRoiCache.mockReturnValue({
      offset: { x: 0, y: 0 },
      size: { x: 320, y: 240 },
    });

    commandService.executeSysAppCommand.mockResolvedValue({
      result: 'SUCCESS',
      command_response: {
        image: 'data:image/png;base64,' + SMALLEST_VALID_PNG,
        res_info: { code: 0 },
      },
    });

    const frame = await service.getNextFrame('dev1', ExtendedMode.Preview);
    expect((frame as DeviceFrame).image).toContain('data:image');
    expect((frame as DeviceFrame).identifier).toBeDefined();
  });

  it('returns Error if image is invalid or res_info.code is non-zero', async () => {
    deviceService.getLastKnownRoiCache.mockReturnValue({
      offset: { x: 0, y: 0 },
      size: { x: 320, y: 240 },
    });

    commandService.executeSysAppCommand.mockResolvedValue({
      command_response: {
        image: '',
        res_info: { code: 999 },
      },
    });

    const frame = await service.getNextFrame('dev1', Mode.ImageOnly);
    expect(frame).toBeInstanceOf(Error);
  });

  it('sets preview to true when mode is ExtendedMode.Preview', async () => {
    deviceService.getLastKnownRoiCache.mockReturnValue({
      offset: { x: 0, y: 0 },
      size: { x: 100, y: 100 },
    });

    commandService.executeSysAppCommand.mockResolvedValue({
      command_response: {
        image: 'img',
        res_info: { code: 0 },
      },
    });

    await service.getNextFrame('dev1', ExtendedMode.Preview);

    expect(commandService.executeSysAppCommand).toHaveBeenCalledWith(
      'dev1',
      expect.objectContaining({
        extra: { preview: true },
      }),
    );
  });

  it('sets preview to false when mode is not ExtendedMode.Preview', async () => {
    deviceService.getLastKnownRoiCache.mockReturnValue({
      offset: { x: 0, y: 0 },
      size: { x: 100, y: 100 },
    });

    commandService.executeSysAppCommand.mockResolvedValue({
      command_response: {
        image: 'img',
        res_info: { code: 0 },
      },
    });

    await service.getNextFrame('dev1', Mode.ImageOnly);

    expect(commandService.executeSysAppCommand).toHaveBeenCalledWith(
      'dev1',
      expect.objectContaining({
        extra: { preview: false },
      }),
    );
  });

  describe('teardown', () => {
    it('should stop inference upload for device', async () => {
      const deviceId = 'dev1';

      await service.teardown(deviceId);
      expect(commandService.executeSysAppCommand).toHaveBeenCalledWith(
        'dev1',
        expect.objectContaining({
          extra: { stop: true },
        }),
      );
    });
  });
});
