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

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Component, EventEmitter, Input, model, Output } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { Configuration, OperationMode } from '@app/core/device/configuration';
import {
  DeviceFrame,
  DeviceStatus,
  LocalDevice,
} from '@app/core/device/device';
import { DeviceVisualizerComponent } from '@app/core/device/device-visualizer/device-visualizer.component';
import { DeviceService } from '@app/core/device/device.service';
import {
  DrawingState,
  SurfaceMode,
} from '@app/core/drawing/drawing-surface.component';
import {
  ModuleConfigService,
  PatchConfigurationMaxAttemptsError,
  PatchConfigurationTimeoutError,
} from '@app/core/module/module-config.service';
import { ToastComponent } from '@app/layout/components/toast/toast';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { ButtonVariant } from '@app/layout/dialogs/user-prompt/action';
import { Configurations } from '@samplers/configuration';
import { Device, DeviceList, DeviceModule } from '@samplers/device';
import { Files } from '@samplers/file';
import { waitForExpect } from '@test/utils';
import { of, Subject } from 'rxjs';
import { DataHubScreen, LabelsStored } from './data-hub.screen';

class MockDeviceService {
  devices$ = of(DeviceList.sample().devices);

  loadDevices = jest.fn();
  deleteDevice = jest.fn();
  updateDeviceName = jest.fn();
  getDevice = jest.fn();
  patchConfiguration = jest.fn();
  getConfiguration = jest.fn();
  getDeviceStream = jest.fn();
  askForDeviceSelection = jest.fn();
}

class MockModuleConfigService implements Partial<ModuleConfigService> {
  patchModuleConfiguration = jest.fn().mockResolvedValue(undefined);
}

class MockDialogService {
  prompt = jest.fn();
  open = jest.fn();
  alert = jest.fn();
}

class MockSnackBar {
  openFromComponent = jest.fn();
}

class MockActivatedRoute {
  queryParams = new Subject<any>();
}

class MockRouter {
  navigate = jest.fn();
}

@Component({
  selector: 'app-device-visualizer',
  standalone: true,
  template: `<div></div>`,
})
export class MockVisualizerComponent {
  @Input() surfaceMode: SurfaceMode = 'render';
  @Input() mode: 'image-only' | 'inferred' = 'image-only';
  @Input() device?: LocalDevice;
  @Output() frameReceived = new EventEmitter<DeviceFrame>();
  @Input() labels: LabelsStored = { labels: [], applied: false };
  __streaming = false;
  error = model(false);
  stopInferenceStream = jest.fn();
  streaming() {
    return this.__streaming;
  }
  @Input() type: OperationMode = 'custom';
  drawingState = model(DrawingState.Disabled);
}

describe('DataHubComponent', () => {
  let component: DataHubScreen;
  let fixture: ComponentFixture<DataHubScreen>;
  let deviceService: MockDeviceService;
  let dialogService: MockDialogService;
  let snackBar: MockSnackBar;
  let visualizer: MockVisualizerComponent;
  let router: MockRouter;
  let route: MockActivatedRoute;
  let modules: jest.Mocked<Partial<ModuleConfigService>>;

  let mockConfiguration: Configuration = {
    device_dir_path: '/tmp/device',
    size: 100,
    auto_deletion: true,
    status: {},
    vapp_type: 'detection',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DataHubScreen, NoopAnimationsModule],
      providers: [
        { provide: DeviceService, useClass: MockDeviceService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: MatSnackBar, useClass: MockSnackBar },
        { provide: ActivatedRoute, useClass: MockActivatedRoute },
        { provide: Router, useClass: MockRouter },
        { provide: ModuleConfigService, useClass: MockModuleConfigService },
      ],
    })
      .overrideComponent(DataHubScreen, {
        remove: { imports: [DeviceVisualizerComponent] },
        add: {
          imports: [MockVisualizerComponent],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(DataHubScreen);
    deviceService = TestBed.inject(
      DeviceService,
    ) as unknown as MockDeviceService;
    dialogService = TestBed.inject(
      DialogService,
    ) as unknown as MockDialogService;
    snackBar = TestBed.inject(MatSnackBar) as unknown as MockSnackBar;
    router = TestBed.inject(Router) as unknown as MockRouter;
    route = TestBed.inject(ActivatedRoute) as unknown as MockActivatedRoute;
    modules = TestBed.inject(ModuleConfigService) as any;
    component = fixture.componentInstance;
    fixture.detectChanges();
    const mockVisualizerDebugElement = fixture.debugElement.query(
      By.directive(MockVisualizerComponent),
    );
    visualizer = mockVisualizerDebugElement.componentInstance;
    component.visualizer = visualizer as unknown as DeviceVisualizerComponent;
    await fixture.whenStable();
    await fixture.whenRenderingDone();

    deviceService.getConfiguration.mockResolvedValue(mockConfiguration);
    deviceService.patchConfiguration.mockResolvedValue(mockConfiguration);
  });

  it('should update parameters', async () => {
    const fileContent = '{"custom_settings":{}}';
    const file = Files.sample('params.json', fileContent);

    await fixture.whenStable();
    await component.onPPLFileSelected(file);

    expect(modules.patchModuleConfiguration).not.toHaveBeenCalled();
    expect(component.pplParameters()).toEqual(JSON.parse(fileContent));
  });

  it('should not update parameters if file is not json', async () => {
    const fileContent = '{not a valid json]';
    const file = Files.sample('params.txt', fileContent);

    component.opMode.set('classification');
    fixture.detectChanges();

    await component.onPPLFileSelected(file);

    expect(dialogService.alert).toHaveBeenCalledWith(
      'PPL Parameters are incorrect',
      `PPL Parameters file must be a valid JSON file, with 'custom_settings' at the top`,
    );

    expect(modules.patchModuleConfiguration).not.toHaveBeenCalled();
    expect(component.pplParameters()).toBe(null);
  });

  it('should not update parameters if not custom_settings', async () => {
    const fileContent = '{"value_a":{}]';
    const file = Files.sample('params.txt', fileContent);

    component.opMode.set('classification');
    fixture.detectChanges();

    await component.onPPLFileSelected(file);

    expect(dialogService.alert).toHaveBeenCalledWith(
      'PPL Parameters are incorrect',
      `PPL Parameters file must be a valid JSON file, with 'custom_settings' at the top`,
    );

    expect(modules.patchModuleConfiguration).not.toHaveBeenCalled();
    expect(component.pplParameters()).toBe(null);
  });

  it('should update labels', async () => {
    const fileContent = 'class_1\nclass2';
    const file = Files.sample('labels.txt', fileContent);

    await fixture.whenStable();

    await component.onLabelsSelected(file);
    expect(component.labels.labels).toEqual(fileContent.split('\n'));
  });

  it('should not update labels if content is not valid', async () => {
    const fileContent = 'not valid!!!!!';
    const file = Files.sample('labels_not_valid.txt', fileContent);

    component.opMode.set('classification');
    fixture.detectChanges();

    await component.onLabelsSelected(file);

    expect(dialogService.alert).toHaveBeenCalledWith(
      'Labels are incorrect',
      `Labels can only contain letters, numbers and underscores.
         There must be no blank lines between labels`,
    );

    expect(component.labels.labels).toStrictEqual([]);
  });

  it('should update labels if user is ok with too long', async () => {
    const fileContent = 'verylonglabeltotriggerwarn';
    const file = Files.sample('labels_too_long.txt', fileContent);

    await fixture.whenStable();
    const result = { id: 'ok' };
    dialogService.prompt.mockResolvedValue(result);
    await component.onLabelsSelected(file);

    expect(dialogService.prompt).toHaveBeenCalledWith({
      message: `Some of the loaded labels have more than 20 characters, which may impact readability.
            Are you sure you want to use these labels? `,
      title: 'Labels are too long',
      actionButtons: [{ id: 'ok', text: 'OK', variant: ButtonVariant.normal }],
      type: 'warning',
      showCancelButton: true,
    });

    expect(component.labels.labels).toStrictEqual([fileContent]);
  });

  it('should not update labels if user cancels if too long', async () => {
    const fileContent = 'verylonglabeltotriggerwarn';
    const file_tl = Files.sample('labels_too_long_2.txt', fileContent);

    await fixture.whenStable();
    const result = undefined;
    dialogService.prompt.mockResolvedValue(result);
    await component.onLabelsSelected(file_tl);

    expect(dialogService.prompt).toHaveBeenCalledWith({
      message: `Some of the loaded labels have more than 20 characters, which may impact readability.
            Are you sure you want to use these labels? `,
      title: 'Labels are too long',
      actionButtons: [{ id: 'ok', text: 'OK', variant: ButtonVariant.normal }],
      type: 'warning',
      showCancelButton: true,
    });

    expect(component.labels.labels).toStrictEqual([]);
  });

  describe('Apply', () => {
    let applyButton: HTMLButtonElement;
    let startButton: HTMLButtonElement;
    beforeEach(() => {
      applyButton = fixture.debugElement.nativeElement.querySelector(
        '[data-testid="apply-configuration"]',
      );
      startButton = fixture.debugElement.nativeElement.querySelector(
        '[data-testid="start-inference-btn"]',
      );
    });

    describe('PFREQ-1511', () => {
      it('CASE 0. Apply button is disabled by default, no device selected', () => {
        expect(applyButton.disabled).toBeTruthy();
        expect(startButton.disabled).toBeTruthy();
      });

      it('CASE 1. Apply button is disabled if PPL params are missing in classification or detection modes', () => {
        // Given User has selected a device in Data hub and mode is not ‘Image capture’
        component.selectedDevice = Device.sample({
          device_name: 'Device 1',
          device_id: '123',
        });
        component.opMode.set('classification');

        //When ‘PPL parameter file’ configuration is missing
        component.pplParameters.set(null);
        fixture.detectChanges();

        // Then Apply and Start buttons are disabled
        expect(applyButton.disabled).toBeTruthy();
        expect(startButton.disabled).toBeTruthy();

        // Repeat for detection mode
        component.opMode.set('detection');
        fixture.detectChanges();

        expect(applyButton.disabled).toBeTruthy();
        expect(startButton.disabled).toBeTruthy();
      });

      it('CASE 2/4. Apply button is disabled and Start button is enabled if device is selected, PPL params present and config has no changes ', () => {
        // Given User has selected a device in Data hub and mode is not ‘Image capture’
        component.selectedDevice = Device.sample({
          device_name: 'Device 1',
          device_id: '123',
        });
        component.selectedDeviceConfiguration.set(Configurations.sample());
        component.opMode.set('classification');
        component.labels.applied = true;

        // When ‘PPL parameter file’ exists and not changed by the user
        component.pplParameters.set(
          DeviceModule.sampleEdgeAppPropertyCustomConfig(),
        );

        // Kind of ridiculous, but the pplTracker depends on effect()
        // that's executed after change detection.
        // And then the button needs another detection cycle to be disabled
        fixture.detectChanges();
        component.selectedDeviceConfigurationTracker.reset();
        component.pplTracker.reset();
        fixture.detectChanges();

        // Then Apply button is disabled and Start button is enabled
        expect(applyButton.disabled).toBeTruthy();
        expect(startButton.disabled).toBeFalsy();
      });

      it('CASE 3. Apply button is enabled and Start button is disabled if preview is stopped and PPL params is touched but not applied', () => {
        // Given User has selected a device in Data hub and mode is not ‘Image capture’
        component.selectedDevice = Device.sample({
          device_name: 'Device 1',
          device_id: '123',
        });
        component.opMode.set('classification');

        // When PPL parameter file exists and is changed by the user and inference is stopped
        component.pplParameters.set(
          DeviceModule.sampleEdgeAppPropertyCustomConfig(),
        );
        expect(component.pplTracker.touched());
        fixture.detectChanges();

        //Then Apply is enabled and Start is disabled
        expect(applyButton.disabled).toBeFalsy();
        expect(startButton.disabled).toBeTruthy();
      });

      it('CASE 5. Apply button is enabled when device is selected and PPL set in non-image capture mode', async () => {
        // When User has started inference
        component.selectedDevice = Device.sample({
          device_name: 'Device 1',
          device_id: '123',
        });
        component.opMode.set('classification');
        component.pplParameters.set(
          DeviceModule.sampleEdgeAppPropertyCustomConfig(),
        );
        visualizer.__streaming = true;
        fixture.destroy(); // nuke old view
        fixture = TestBed.createComponent(DataHubScreen); // recreate fresh with updated state
        fixture.detectChanges();

        // Then Apply button is disabled
        expect(applyButton.disabled).toBeTruthy();
      });

      it('CASE ø. Apply button is enabled if PPL params are missing in image capture mode', () => {
        // Given User has selected a device in Data hub and mode is not ‘Image capture’
        component.selectedDevice = Device.sample({
          device_name: 'Device 1',
          device_id: '123',
        });
        component.opMode.set('image');

        //When ‘PPL parameter file’ configuration is missing
        component.pplParameters.set(null);
        fixture.detectChanges();

        // Then both Apply and Start are enabled
        expect(component.isApplyEnabled()).toBeTruthy();
        expect(startButton.disabled).toBeTruthy();
      });
    });

    it('Apply button is disabled when device is not Connected', () => {
      // Given
      component.selectedDevice = Device.sample({
        device_name: 'Device 1',
        device_id: '123',
        connection_state: DeviceStatus.Disconnected,
      });

      // When
      component.opMode.set('classification');
      component.pplParameters.set(
        DeviceModule.sampleEdgeAppPropertyCustomConfig(),
      );
      visualizer.__streaming = true;
      fixture.destroy(); // nuke old view
      fixture = TestBed.createComponent(DataHubScreen); // recreate fresh with updated state
      fixture.detectChanges();

      // Then
      expect(applyButton.disabled).toBeTruthy();
    });

    it('Start button is disabled when device is not Connected', () => {
      // Given
      component.selectedDevice = Device.sample({
        device_name: 'Device 1',
        device_id: '123',
        connection_state: DeviceStatus.Disconnected,
      });
      component.selectedDeviceConfiguration.set(Configurations.sample());
      component.opMode.set('classification');
      component.labels.applied = true;

      // When ‘PPL parameter file’ exists and not changed by the user
      component.pplParameters.set(
        DeviceModule.sampleEdgeAppPropertyCustomConfig(),
      );

      // Kind of ridiculous, but the pplTracker depends on effect()
      // that's executed after change detection.
      // And then the button needs another detection cycle to be disabled
      fixture.detectChanges();
      component.selectedDeviceConfigurationTracker.reset();
      component.pplTracker.reset();
      fixture.detectChanges();

      expect(startButton.disabled).toBeTruthy();
    });

    it('should call updateModuleConfigurationV2 when apply is clicked', async () => {
      const device = Device.sample({
        device_name: 'Device 1',
        device_id: '123',
      });

      const pplParameters = DeviceModule.sampleEdgeAppPropertyCustomConfig();
      component.selectedDevice = device;
      component.pplParameters.set(pplParameters);
      fixture.detectChanges();

      expect(applyButton.disabled).not.toBeTruthy();
      await component.onApply();

      expect(modules.patchModuleConfiguration).toHaveBeenCalled();
      expect(snackBar.openFromComponent).toHaveBeenCalledWith(ToastComponent, {
        data: {
          message: 'Configuration Applied',
          panelClass: 'success-snackbar',
        },
        duration: 3000,
      });
    });

    it('should set applying to false after successful onApply', async () => {
      modules.patchModuleConfiguration = jest.fn().mockResolvedValue(undefined);
      deviceService.patchConfiguration.mockResolvedValue(
        Configurations.sample(),
      );

      component.pplParameters.set({
        custom_settings: { ai_models: { one_pass_model: undefined } },
      });
      component.selectedDevice = Device.sample();
      component.selectedDeviceConfiguration.set(mockConfiguration);

      const applied = await component.onApply();

      expect(applied).toBeTruthy();
      expect(component.applying).toBe(false);
      expect(snackBar.openFromComponent).toHaveBeenCalled();
    });

    it('should show alert on PatchConfigurationTimeoutError and set applying to false', async () => {
      jest.useFakeTimers();

      modules.patchModuleConfiguration = jest
        .fn()
        .mockRejectedValue(new PatchConfigurationTimeoutError(60000));

      component.pplParameters.set({
        custom_settings: { ai_models: { one_pass_model: undefined } },
      });
      component.selectedDevice = Device.sample();
      component.selectedDeviceConfiguration.set(mockConfiguration);

      const applied = await component.onApply();
      await jest.runAllTimersAsync();

      expect(applied).toBeFalsy();
      expect(component.applying).toBe(false);
      expect(dialogService.alert).toHaveBeenCalledWith(
        'Error applying configuration',
        expect.stringContaining('timeout exceeded'),
      );

      jest.useRealTimers();
    });

    it('should show alert on PatchConfigurationMaxAttemptsError and set applying to false', async () => {
      jest.useFakeTimers();

      modules.patchModuleConfiguration = jest
        .fn()
        .mockRejectedValue(new PatchConfigurationMaxAttemptsError(100));

      component.pplParameters.set({
        custom_settings: { ai_models: { one_pass_model: undefined } },
      });
      component.selectedDevice = Device.sample();
      component.selectedDeviceConfiguration.set(mockConfiguration);

      await component.onApply();
      await jest.runAllTimersAsync();

      expect(component.applying).toBe(false);
      expect(dialogService.alert).toHaveBeenCalledWith(
        'Error applying configuration',
        expect.stringContaining('max attempts exceeded'),
      );

      jest.useRealTimers();
    });
  });

  it('should not call configure when mode changes', async () => {
    const device = Device.sample({
      device_name: 'Device 1',
      device_id: '123',
    });

    component.selectedDevice = device;
    fixture.detectChanges();

    component.opMode.set('detection');
    fixture.detectChanges();

    expect(deviceService.patchConfiguration).not.toHaveBeenCalled();
  });

  it('should update destination directory path when onDestinationFolderSelected is called', () => {
    const device = Device.sample({
      device_name: 'Device 1',
      device_id: '123',
    });
    component.selectedDevice = device;

    const folderPath = '/path/to/inference';
    component.onDestinationFolderSelected({ path: folderPath });
    expect(component.selectedDeviceConfiguration().device_dir_path).toBe(
      folderPath,
    );
  });

  it('should disable automatic file deletion when folders change', async () => {
    // Given
    const device = Device.sample({
      device_name: 'Device 1',
      device_id: '123',
    });
    component.selectedDevice = device;
    fixture.detectChanges();
    const folderPath = '/path/to/data';
    component.selectedDeviceConfiguration.update((cfg) => ({
      ...cfg,
      auto_deletion: true,
    }));

    // When
    await component.onDestinationFolderSelected({ path: folderPath });

    // Then
    expect(component.selectedDeviceConfiguration().auto_deletion).toBeFalsy();
  });

  it('should disable automatic file deletion when quota changes', () => {
    // Given
    const device = Device.sample({
      device_name: 'Device 1',
      device_id: '123',
    });
    component.selectedDevice = device;
    fixture.detectChanges();

    component.selectedDeviceConfiguration.update((cfg) => ({
      ...cfg,
      size: 50,
      auto_deletion: true,
    }));

    // When
    component.onStorageSizeChange(100);

    // Then
    expect(component.selectedDeviceConfiguration().auto_deletion).toBeFalsy();
  });

  it('should apply changes and labels', async () => {
    const MODULE_ID = 'node';
    const pplParams = DeviceModule.sampleEdgeAppPropertyCustomConfig();
    await fixture.whenStable();

    component.selectedDevice = Device.sample();
    component.pplParameters.set(pplParams);
    fixture.detectChanges();
    component.opMode.set('classification');
    fixture.detectChanges();

    await component.onApply();

    expect(modules.patchModuleConfiguration).toHaveBeenCalledWith(
      component.selectedDevice?.device_id,
      MODULE_ID,
      pplParams,
    );

    expect(deviceService.patchConfiguration).toHaveBeenCalledWith(
      component.selectedDevice?.device_id,
      {
        vapp_type: 'classification',
        size: 100,
      },
    );
  });

  it('should store config if selectedDevice is not null', async () => {
    component.selectedDevice = Device.sample();
    var sample_device: LocalDevice = Device.sample();
    deviceService.askForDeviceSelection.mockResolvedValue(sample_device);

    mockConfiguration.size = 444;
    deviceService.getConfiguration.mockResolvedValue(mockConfiguration);

    await component.openDeviceSelectionDialog();

    expect(deviceService.askForDeviceSelection).toHaveBeenCalledWith(
      component.selectedDevice,
    );
    expect(deviceService.getConfiguration).toHaveBeenCalledWith(
      component.selectedDevice?.device_id,
    );
    fixture.detectChanges();
    await fixture.whenStable();
    expect(component.selectedDevice).toBe(sample_device);
    expect(component.selectedDeviceConfiguration().size).toBe(444);
    expect(component.selectedDeviceConfiguration().vapp_type).toBe('detection');
  });

  it('should not store config if selectedDevice is null', async () => {
    var pre_config: Configuration = component.selectedDeviceConfiguration();
    deviceService.askForDeviceSelection.mockResolvedValue(undefined);
    await component.openDeviceSelectionDialog();

    expect(deviceService.askForDeviceSelection).toHaveBeenCalledWith(
      component.selectedDevice,
    );
    expect(await deviceService.getConfiguration).not.toHaveBeenCalled();

    expect(component.selectedDevice).toBe(undefined);
    expect(component.selectedDeviceConfiguration()).toBe(pre_config);
  });

  it('should apply changes and labels without confirmation', async () => {
    const MODULE_ID = 'node';
    const pplParams = DeviceModule.sampleEdgeAppPropertyCustomConfig();
    const configurationSize = 100;

    await fixture.whenStable();

    component.selectedDevice = Device.sample();
    component.pplParameters.set(pplParams);
    component.opMode.set('classification');
    fixture.detectChanges();
    component.selectedDeviceConfiguration.update((cfg) => ({
      ...cfg,
      size: configurationSize,
    }));
    component.selectedDeviceConfigurationTracker.reset();
    fixture.detectChanges();

    await component.onApply();

    expect(dialogService.prompt).not.toHaveBeenCalled();

    expect(modules.patchModuleConfiguration).toHaveBeenCalledWith(
      component.selectedDevice?.device_id,
      MODULE_ID,
      pplParams,
    );

    expect(await deviceService.patchConfiguration).toHaveBeenCalledWith(
      component.selectedDevice?.device_id,
      {
        vapp_type: 'classification',
        size: configurationSize,
      },
    );
  });

  it('should not patch module configuration in Image Capture mode', async () => {
    const pplParams = DeviceModule.sampleEdgeAppPropertyCustomConfig();

    await fixture.whenStable();

    component.selectedDevice = Device.sample();
    component.pplParameters.set(pplParams);
    component.opMode.set('image');
    fixture.detectChanges();

    component.selectedDeviceConfigurationTracker.reset();
    fixture.detectChanges();

    const applied = await component.onApply();

    expect(modules.patchModuleConfiguration).not.toHaveBeenCalled();
    expect(deviceService.patchConfiguration).toHaveBeenCalled();
    expect(applied).toBeTruthy();
  });

  describe('Error hints', () => {
    it('should refresh hints after selecting device', async () => {
      component.parseStatus = jest.fn();

      mockConfiguration.status = {
        STORAGE_USAGE: {
          value: 3,
        },
        FOLDER_ERROR: {
          value: null,
        },
      };

      component.selectedDevice = Device.sample();
      let sample_device: LocalDevice = Device.sample();
      deviceService.askForDeviceSelection.mockResolvedValue(sample_device);

      expect(component.parseStatus).not.toHaveBeenCalled();

      await component.openDeviceSelectionDialog();

      fixture.detectChanges();
      await fixture.whenStable();
      expect(deviceService.getConfiguration).toHaveBeenCalled();
      expect(component.parseStatus).toHaveBeenCalledWith(
        mockConfiguration.status,
      );
    });

    it('should parse status after clicking Apply', async () => {
      component.parseStatus = jest.fn();

      mockConfiguration.status = {
        STORAGE_USAGE: {
          value: 3,
        },
        FOLDER_ERROR: {
          value: null,
        },
      };

      component.selectedDevice = Device.sample();
      let sample_device: LocalDevice = Device.sample();
      deviceService.askForDeviceSelection.mockResolvedValue(sample_device);

      expect(component.parseStatus).not.toHaveBeenCalled();

      await component.onApply();

      expect(await deviceService.patchConfiguration).toHaveBeenCalled();
      expect(component.parseStatus).toHaveBeenCalledWith(
        mockConfiguration.status,
      );
    });

    it('should show quota hint if exceeds size', async () => {
      let status = {
        STORAGE_USAGE: {
          value: component.selectedDeviceConfiguration().size! * 1024 * 1024,
        },
      };

      component.parseStatus(status);

      expect(component.showQuotaHint()).toBeFalsy();

      status.STORAGE_USAGE.value += 1;

      component.parseStatus(status);

      expect(component.showQuotaHint()).toBeTruthy();
    });

    it('should show destination folder hint if folder error', async () => {
      component.parseStatus({
        FOLDER_ERROR: {
          value: null,
        },
      });

      expect(component.showDestinationFolderHint()).toBeTruthy();

      component.parseStatus({});

      expect(component.showDestinationFolderHint()).toBeFalsy();
    });
  });

  describe('DataHubScreen queryParams handling', () => {
    it('should ignore unrelated query params and not trigger device loading', async () => {
      route.queryParams.next({});
      await fixture.whenStable();

      expect(deviceService.getDevice).not.toHaveBeenCalled();
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('should handle multiple relevant query params correctly', async () => {
      const mockDevice = Device.sample();
      deviceService.getDevice.mockResolvedValue(mockDevice);

      route.queryParams.next({ deviceId: 'device123', state: 'quota-hit' });
      fixture.detectChanges();
      await fixture.whenStable();

      expect(deviceService.getDevice).toHaveBeenCalledWith('device123', true);
      fixture.detectChanges();
      await waitForExpect(() => {
        expect(visualizer.stopInferenceStream).toHaveBeenCalled();
        expect(component.storageHighlight()).toBeFalsy();
      });
      await waitForExpect(() => {
        expect(component.storageHighlight()).toBeTruthy();
      });
      expect(router.navigate).toHaveBeenCalledWith([], {
        queryParams: {},
        replaceUrl: true,
      });
    });
  });
});
