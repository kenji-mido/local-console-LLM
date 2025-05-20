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
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { LocalDevice } from '@app/core/device/device';
import { DeviceService } from '@app/core/device/device.service';
import { Subject } from 'rxjs';
import { HttpApiClient } from '../../../core/common/http/http';
import { LoadingScreen } from './loading.screen';

class MockDeviceService {
  devices$ = new Subject<LocalDevice[]>();
  loadDevices = jest.fn();
}

describe('LoaderComponent', () => {
  let component: LoadingScreen;
  let fixture: ComponentFixture<LoadingScreen>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [LoadingScreen, NoopAnimationsModule],
      providers: [
        { provide: DeviceService, useClass: MockDeviceService },
        { provide: HttpApiClient, useClass: HttpApiClient },
        provideHttpClient(),
        provideHttpClientTesting(), // Mock actual HTTP requests
      ],
    });
    fixture = TestBed.createComponent(LoadingScreen);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
