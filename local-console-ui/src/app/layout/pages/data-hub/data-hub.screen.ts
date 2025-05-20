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

import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  Component,
  effect,
  inject,
  model,
  signal,
  TemplateRef,
  ViewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ActivatedRoute, Router } from '@angular/router';
import { debounce } from '@app/core/common/debounce';
import {
  Configuration,
  ConfigurationStatus,
  OperationMode,
} from '@app/core/device/configuration';
import {
  DeviceFrame,
  DeviceStatus,
  LocalDevice,
} from '@app/core/device/device';
import { DeviceService } from '@app/core/device/device.service';
import { InfotipDirective } from '@app/core/feedback/infotip.component';
import { InferenceLike, Mode } from '@app/core/inference/inference';
import { EdgeAppModuleEdgeAppV2 } from '@app/core/module/edgeapp';
import {
  ModuleConfigService,
  PatchConfigurationMaxAttemptsError,
  PatchConfigurationTimeoutError,
} from '@app/core/module/module-config.service';
import {
  NotificationKind,
  NotificationsService,
} from '@app/core/notification/notifications.service';
import { signalTracker } from '@app/core/signal/signal-tracker';
import { NumberSpinnerComponent } from '@app/layout/components/number-spinner/number-spinner.component';
import { ToastComponent } from '@app/layout/components/toast/toast';
import { DialogService } from '@app/layout/dialogs/dialog.service';
import { action } from '@app/layout/dialogs/user-prompt/action';
import { DeviceVisualizerComponent } from '../../../core/device/device-visualizer/device-visualizer.component';
import {
  FileInformationEvented,
  FileInputComponent,
} from '../../../core/file/file-input/file-input.component';
import {
  FolderInformation,
  FolderPickerComponent,
} from '../../../core/file/folder-path-input/folder-picker.component';
import { IconTextComponent } from '../../../core/file/icon-text/icon-text.component';
import {
  InferenceDisplayComponent,
  InferenceDisplayMode,
} from '../../../core/inference/inference-display/inference-display.component';
import { SegmentsComponent } from '../../../core/option/segments.component';
import { OperationModeType } from './data-hub';

const MODULE_ID = 'node';

export interface LabelsStored {
  labels: string[];
  applied: boolean;
}

export interface InferenceHubCommand {
  deviceId: string;
  state: 'quota-hit';
}

export interface InferenceHubRouteParameters extends InferenceHubCommand {
  __rid: string; // Random identifier, just to signal Angular to re-do similar messages
}

@Component({
  selector: 'app-data-hub',
  templateUrl: './data-hub.screen.html',
  styleUrls: ['./data-hub.screen.scss'],
  standalone: true,
  imports: [
    MatSelectModule,
    FormsModule,
    FileInputComponent,
    IconTextComponent,
    InfotipDirective,
    FolderPickerComponent,
    NumberSpinnerComponent,
    DeviceVisualizerComponent,
    InferenceDisplayComponent,
    CommonModule,
    SegmentsComponent,
    MatProgressSpinner,
  ],
})
export class DataHubScreen implements AfterViewInit {
  theme = 'light';
  InferenceDisplayMode = InferenceDisplayMode;

  pplParameters = model<Pick<
    EdgeAppModuleEdgeAppV2,
    'custom_settings'
  > | null>();
  pplTracker = signalTracker(this.pplParameters);
  Mode = Mode;
  storageHighlight = signal(false);

  selectedDevice?: LocalDevice;
  selectedDeviceConfiguration = model<Configuration>({
    size: 100,
    vapp_type: 'classification',
  });
  opMode = model<OperationMode | undefined>('classification');
  selectedDeviceConfigurationTracker = signalTracker(
    this.selectedDeviceConfiguration,
  );
  labels: LabelsStored = { labels: [], applied: false };
  stop?: Function;
  inference?: InferenceLike;

  showHint = signal(false);
  showDestinationFolderHint = signal(false);
  showQuotaHint = signal(false);
  statusCheckDebounced = debounce(this.getStatusAndCheck.bind(this), 500);
  applying = false;

  @ViewChild(DeviceVisualizerComponent) visualizer?: DeviceVisualizerComponent;
  @ViewChild('paramsFile') paramsFile!: FileInputComponent;
  @ViewChild('modelFile') labelsFile!: FileInputComponent;
  @ViewChild('enableAutoDeletionTpl')
  autoDeletionConfirmationPrompt!: TemplateRef<any>;

  public snackBar = inject(MatSnackBar);
  constructor(
    private deviceService: DeviceService,
    private modules: ModuleConfigService,
    private prompts: DialogService,
    private route: ActivatedRoute,
    private router: Router,
    notifications: NotificationsService,
  ) {
    notifications
      .on<any>(NotificationKind.DEVICE_NO_QUOTA)
      .pipe(takeUntilDestroyed())
      .subscribe((data) => {
        this.processCommand({
          deviceId: data.device_id,
          state: 'quota-hit',
        });
      });
    effect(
      () => {
        const mode = this.opMode();
        this.selectedDeviceConfiguration.update((cfg) => ({
          ...cfg,
          vapp_type: mode,
        }));
      },
      { allowSignalWrites: true },
    );
  }

  ngAfterViewInit() {
    this.route.queryParams.subscribe((pars) => {
      if (Object.keys(pars).length === 0) return; // Ignore no parameters
      const params = pars as InferenceHubRouteParameters;
      this.processCommand(params);
    });
  }

  checkLettersSpaces(strings: string[]): boolean {
    const regex = /^[a-zA-Z0-9_]+$/; // Matches only letters, numbers, and underscores
    return strings.every((str) => regex.test(str) && str.length > 0); //Max number of chars is 20 and can not be empty
  }

  checkCharsLength(strings: string[]): boolean {
    return strings.some((str) => str.length >= 20); //If number of chars is >20
  }

  isSizeUpdated(
    prevSize: number | null | undefined,
    currSize: number | null | undefined,
  ): boolean {
    return Number(prevSize ?? 0) > Number(currSize ?? 0);
  }

  isFolderUpdated(
    prevFolder: string | null | undefined,
    currFolder: string | null | undefined,
  ): boolean {
    return prevFolder !== currFolder;
  }

  isApplyEnabled(): boolean {
    if (this.selectedDevice?.connection_state !== DeviceStatus.Connected)
      return false;

    if (this.visualizer?.streaming()) return false;

    if (this.statusCheckDebounced.running()) return false;

    if (this.showDestinationFolderHint()) return false;

    // If in 'image' mode, enable if any modification of property
    if (this.selectedDeviceConfiguration().vapp_type === 'image') {
      return this.selectedDeviceConfigurationTracker.touched();
    }

    // In the rest of modes, PPL Parameters is a **required** attribute

    // If PPL Parameters are missing => disable
    if (!this.pplParameters()) {
      return false;
    }

    // If PPL Parameters has been modified => enable
    if (this.pplTracker.touched()) {
      return true;
    }

    // If labels hasn't been applied => enable
    if (!this.labels.applied) return true;

    // If any property has changed => enable
    return this.selectedDeviceConfigurationTracker.touched();
  }

  isStartEnabled() {
    if (this.selectedDevice?.connection_state !== DeviceStatus.Connected)
      return false;

    if (this.visualizer?.streaming()) return false;

    if (this.statusCheckDebounced.running()) return false;

    if (this.showDestinationFolderHint()) return false;

    if (this.isApplyEnabled()) return false;

    // PPL Parameters are mandatory
    if (
      this.selectedDeviceConfiguration().vapp_type !== 'image' &&
      !this.pplParameters()
    )
      return false;

    return true;
  }

  onModeChange() {
    if (this.selectedDeviceConfiguration().vapp_type === 'image') {
      this.pplParameters.set(null);
      this.pplTracker.reset();
    }
  }

  cleanTrailingBlanks(strings: string[]): string[] {
    let lastIndex = strings.length - 1;

    const trimmedStrings = strings.map((str) => str.trim());
    // Find the last non-empty string
    while (lastIndex >= 0 && trimmedStrings[lastIndex] === '') {
      lastIndex--;
    }

    // Return a new array up to the last non-empty string
    return trimmedStrings.slice(0, lastIndex + 1);
  }

  async onLabelsSelected(labelsFileInfo: FileInformationEvented) {
    let dec = new TextDecoder();
    let labels = dec.decode(labelsFileInfo.data);
    const labels_arr: string[] = this.cleanTrailingBlanks(labels.split('\n'));

    if (!this.checkLettersSpaces(labels_arr)) {
      const labels_error: string = `Labels can only contain letters, numbers and underscores.
         There must be no blank lines between labels`;
      await this.prompts.alert('Labels are incorrect', labels_error);
      this.labels.labels = [];
      this.labelsFile.reset();
    } else {
      if (this.checkCharsLength(labels_arr)) {
        const result = await this.prompts.prompt({
          message: `Some of the loaded labels have more than 20 characters, which may impact readability.
            Are you sure you want to use these labels? `,
          title: 'Labels are too long',
          actionButtons: [action.normal('ok', 'OK')],
          type: 'warning',
          showCancelButton: true,
        });
        if (result === undefined) {
          return;
        }
      }
      if (this.labels.labels != labels_arr) {
        this.labels.applied = false;
      }
      this.labels.labels = labels_arr;
    }
  }

  async onPPLFileSelected(paramsFile: FileInformationEvented) {
    let dec = new TextDecoder();
    let params = dec.decode(paramsFile.data);
    try {
      const config = JSON.parse(params);
      if (Object.hasOwn(config, 'custom_settings')) {
        this.pplParameters.set({ custom_settings: config.custom_settings });
        return;
      }
    } catch (e) {
      console.error('File is not JSON', e);
    }
    this.paramsFile.reset();
    this.pplParameters.set(null);
    const labels_error: string = `PPL Parameters file must be a valid JSON file, with 'custom_settings' at the top`;
    await this.prompts.alert('PPL Parameters are incorrect', labels_error);
  }

  async onApply() {
    this.applying = true;
    try {
      this.statusCheckDebounced.cancel();
      const custom_settings = this.pplParameters()?.custom_settings;
      if (custom_settings && this.opMode() !== 'image') {
        await this.modules.patchModuleConfiguration(
          this.selectedDevice!.device_id,
          MODULE_ID,
          { custom_settings },
        );
      }

      const config = await this.deviceService.patchConfiguration(
        this.selectedDevice!.device_id,
        this.selectedDeviceConfiguration(),
      );

      this.labels.applied = true;

      this.selectedDeviceConfigurationTracker.reset();
      this.pplTracker.reset();
      this.snackBar.openFromComponent(ToastComponent, {
        data: {
          message: 'Configuration Applied',
          panelClass: 'success-snackbar',
        },
        duration: 3000,
      });
      this.showHint.set(false);
      this.parseStatus(config.status);
      return true;
    } catch (e) {
      let errorMessage =
        'Something has gone wrong when trying to apply the configuration to the device.' +
        ' Check that the device is connected and that an Edge Application has been deployed to it.';
      if (
        e instanceof PatchConfigurationTimeoutError ||
        e instanceof PatchConfigurationMaxAttemptsError
      ) {
        errorMessage =
          e.message +
          '. Ensure the device has an Edge Application deployed and try again.';
      }
      await this.prompts.alert('Error applying configuration', errorMessage);
      return false;
    } finally {
      this.applying = false;
    }
  }

  async openDeviceSelectionDialog() {
    const device = await this.deviceService.askForDeviceSelection(
      this.selectedDevice,
    );
    this.setDeviceAndLoadConfig(device);
  }

  private async setDeviceAndLoadConfig(device?: LocalDevice) {
    if (device) {
      const config = await this.deviceService.getConfiguration(
        device.device_id,
      );

      // assignment order ensures device-visualizer to render correct mode
      this.selectedDevice = device;

      this.selectedDeviceConfiguration.set(config);
      this.opMode.set(config.vapp_type);
      this.selectedDeviceConfigurationTracker.touch();
      this.inference = undefined;

      this.showHint.set(false);
      this.parseStatus(config.status);
    }
  }

  getModelName(model: OperationModeType | null | undefined) {
    if (model === 'classification') return 'Brain Builder Classifier';
    if (model === 'detection') return 'Brain Builder Detector';
    if (model === 'generic_classification') return 'Classification';
    if (model === 'generic_detection') return 'Object Detection';
    if (model === 'custom') return 'User App';
    return '';
  }

  getModeName(model: OperationModeType | null | undefined) {
    if (model === 'image') return 'Image';
    return 'Image & Inference';
  }

  onFrameReceived(frame: DeviceFrame) {
    if (!frame.inference) return;
    this.inference = frame.inference;
  }

  onDestinationFolderSelected(folderInfo: FolderInformation) {
    const config = this.selectedDeviceConfiguration();
    if (config.device_dir_path === folderInfo.path) return;

    if (config.auto_deletion) this.showHint.set(true);
    this.selectedDeviceConfiguration.set({
      ...config,
      device_dir_path: folderInfo.path,
      auto_deletion: false,
    });
    this.statusCheckDebounced();
  }

  onStorageSizeChange(val: number) {
    const config = this.selectedDeviceConfiguration();
    if (config.size === val) return;

    if (config.auto_deletion) this.showHint.set(true);
    this.selectedDeviceConfiguration.set({
      ...config,
      size: val,
      auto_deletion: false,
    });
    this.statusCheckDebounced();
  }

  async onAutoDeletionChange(state: string) {
    const config = this.selectedDeviceConfiguration();
    console.log(config.auto_deletion);
    let newState = state === 'On';
    if (newState) {
      const result = await this.prompts.prompt({
        showCancelButton: false,
        type: 'warning',
        actionButtons: [
          action.weak('disable', 'Keep it disabled'),
          action.normal('enable', 'Enable'),
        ],
        title: 'Enable Automatic File Deletion?',
        message: this.autoDeletionConfirmationPrompt,
      });
      console.log(result);
      newState = result?.id === 'enable';
      if (newState) this.showHint.set(false);
      console.log(newState);
    }
    this.selectedDeviceConfiguration.set({
      ...config,
      auto_deletion: newState,
    });
  }

  startStreaming() {
    this.showQuotaHint.set(false);
    if (!this.visualizer) return;
    this.visualizer.startPreview();
  }

  stopStreaming() {
    this.inference = undefined;
    this.visualizer?.stopInferenceStream();
  }

  async getStatusAndCheck() {
    if (!this.selectedDevice) return;

    this.parseStatus(
      (
        await this.deviceService.patchConfiguration(
          this.selectedDevice!.device_id,
          {
            device_dir_path: this.selectedDeviceConfiguration().device_dir_path,
          },
          true,
        )
      ).status,
    );
  }

  parseStatus(status?: ConfigurationStatus) {
    if (!status) return;

    this.showDestinationFolderHint.set(!!status.FOLDER_ERROR);
    this.showQuotaHint.set(
      !!status.STORAGE_USAGE &&
        status.STORAGE_USAGE.value >
          this.selectedDeviceConfiguration().size! * 1024 * 1024,
    );
  }

  private async processCommand(command: InferenceHubCommand) {
    const newDevice = await this.deviceService.getDevice(
      command.deviceId,
      true,
    );
    await this.setDeviceAndLoadConfig(newDevice);

    if (command.state === 'quota-hit') {
      setTimeout(() => this.stopStreaming());
      this.highlightStorage();
    }
    // Cleanup params from URL - in case of F5 or any other refresh
    this.router.navigate([], { queryParams: {}, replaceUrl: true });
  }

  private highlightStorage() {
    // Resetting just in case it's not the first time. 500ms for CSS refresh
    this.storageHighlight.set(false);
    setTimeout(() => {
      this.storageHighlight.set(true);
    }, 500);
  }
}
