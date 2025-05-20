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
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { NICService } from '@app/core/nic/nic.service';
import { NICS } from '@samplers/nics';
import { QrService } from '../../../../core/qr/qr.service';
import { NetworkSettingsPane } from './network-settings.pane';

// Mock QR Service
class MockQrService {
  generateQrCode = jest.fn().mockResolvedValue({
    result: 'SUCCESS',
    contents: 'image_bytes_here_as_base64',
    expiration_date: new Date(
      new Date().getTime() + 1000 * 60 * 60,
    ).toISOString(),
  });
}

class MockNICService {
  getAvailableNICs = jest.fn().mockResolvedValue(NICS.sampleList());
}

describe('NetworkSettingsPane', () => {
  let component: NetworkSettingsPane;
  let fixture: ComponentFixture<NetworkSettingsPane>;
  let qrService: MockQrService;
  let nicService: MockNICService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ReactiveFormsModule,
        FormsModule,
        NetworkSettingsPane,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: QrService, useClass: MockQrService },
        { provide: NICService, useClass: MockNICService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(NetworkSettingsPane);
    component = fixture.componentInstance;
    qrService = TestBed.inject(QrService) as unknown as MockQrService;
    nicService = TestBed.inject(NICService) as unknown as MockNICService;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should call QR service on generateQRCode and handle results correctly', async () => {
    await component.generateQRCode();
    expect(qrService.generateQrCode).toHaveBeenCalled();
    expect(component.qrImage).toContain(
      'data:image/jpeg;base64,image_bytes_here_as_base64',
    );
    expect(component.qrExpiredDate).toBeDefined();
    expect(component.qrDisplay).toBeTruthy();
  });

  it('should emit qrCode event with correct data', async () => {
    const emitSpy = jest.spyOn(component.qrCode, 'emit');
    await component.generateQRCode();
    expect(emitSpy).toHaveBeenCalledWith({
      qrCode: component.qrImage,
      qrCreatedDate: component.qrCreatedDate,
      qrExpiredDate: component.qrExpiredDate,
    });
  });

  it('should handle errors from QR service correctly', async () => {
    qrService.generateQrCode.mockRejectedValue(
      new Error('Failed to generate QR'),
    );
    await component.generateQRCode();
    expect(component.qrImage).toEqual('');
    expect(component.qrLoading).toBeFalsy();
    expect(component.qrDisplay).toBeTruthy(); // Still shows the QR code area, possibly with an error message
  });

  it('should reset the form to initial values on clearAll', () => {
    component.clearAll();
    expect(component.qrcodeFormGroup.value).toEqual(
      expect.objectContaining(component.qrcodeFormGroupInit),
    );
  });

  it('should reset the wifi settings', () => {
    component.onWifiSettingsToggle();
    expect(component.qrcodeFormGroup.controls['wifi_pass'].value).toEqual(null);
    expect(component.qrcodeFormGroup.controls['wifi_ssid'].value).toEqual(null);
  });

  it('should reset the network settings', () => {
    component.onNetworkConfigToggle();
    expect(component.qrcodeFormGroup.controls['ip_address'].value).toEqual(
      null,
    );
    expect(component.qrcodeFormGroup.controls['subnet_mask'].value).toEqual(
      null,
    );
    expect(component.qrcodeFormGroup.controls['gateway'].value).toEqual(null);
    expect(component.qrcodeFormGroup.controls['dns'].value).toEqual(null);
  });

  it('should update port', async () => {
    const port = 12345;
    component.mqttPort = port;

    await component.generateQRCode();
    expect(qrService.generateQrCode).toHaveBeenCalledWith(
      expect.objectContaining({
        mqtt_port: port,
      }),
    );
  });

  it('should load NICs on creation', () => {
    expect(nicService.getAvailableNICs).toHaveBeenCalledTimes(1);

    expect(component.availableNics.loading()).toBeFalsy();
    expect(component.availableNics.error()).toBeFalsy();
    expect(component.availableNics.data()).toHaveLength(3);
  });
});
