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

import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { ROUTER_LINKS } from '../../config/routes';
import { UserPromptDialogData } from '../../../layout/dialogs/user-prompt/user-prompt.dialog';
import { HttpErrorResponse } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { DialogService } from '../../../layout/dialogs/dialog.service';

const API_ERR_TITLE = 'Processing failed.';
const API_WARNING_TITLE =
  'The process is complete, but the following warning has occurred.';

const API_INTERNAL_SERVER_ERROR = 'Internal server error.';

interface ErrorMessageContent {
  title: string;
  message: string;
  type: UserPromptDialogData['type'];
}

@Injectable({
  providedIn: 'root',
})
export class HttpErrorHandler {
  constructor(
    private router: Router,
    private dialog: DialogService,
  ) {}

  handleError(e: HttpErrorResponse, showAlert = true): never {
    const { error } = e;
    const errorText = JSON.stringify(error);
    if (e.status === 401) {
      this.redirectToLogin();
      throw '';
    }
    if (errorText.includes('maintainers-page')) {
      this.router.navigate([ROUTER_LINKS.ERROR], {
        state: { content: errorText },
      });
      throw '';
    }
    if (e.status === 503) {
      this.router.navigate([ROUTER_LINKS.MAINTENANCE]);
      throw '';
    }
    if (showAlert) {
      const { title, message, type } = this.getErrorMessage(e);
      this.dialog.alert(title, message, type);
    }
    throw e;
  }

  handleWarning(data: any, showAlert = true) {
    if (
      showAlert &&
      data &&
      data.message &&
      data.message !== '' &&
      data.result === 'WARNING' &&
      // workaround requested by SCSW-23558
      data.code !== 'W.SC.API.0212003'
    ) {
      this.dialog.alert(
        API_WARNING_TITLE,
        `· detail: ${data.message} (${data.code})`,
        'warning',
      );
    }
  }

  public handlePromise<T>(p: Promise<T>, showErrorAlert = true) {
    return p
      .then((data: any) => {
        this.handleWarning(data, showErrorAlert);
        return data;
      })
      .catch((err) => {
        this.handleError(err, showErrorAlert);
      });
  }

  getErrorMessage(err: any): ErrorMessageContent {
    let errMsgContent: ErrorMessageContent = {
      title: API_ERR_TITLE,
      message: '',
      type: 'error',
    };
    const errorCodes = [200, 400, 403, 404, 409, 416, 422, 500, 503];
    if (errorCodes.includes(err.status) && err.error.message) {
      if (err.error.result && err.error.result !== 'SUCCESS')
        errMsgContent.message = `${err.error.message} (${err.error.code})`;
      if (err.error.result === 'WARNING') {
        errMsgContent.title = API_WARNING_TITLE;
        errMsgContent.type = 'warning';
      }
    } else if (err.status !== undefined) {
      errMsgContent.message = err.statusText;
    } else {
      errMsgContent.message = API_INTERNAL_SERVER_ERROR;
    }
    return errMsgContent;
  }

  redirectToLogin() {
    const projectId = localStorage.getItem('project_id');
    if (
      location.pathname !== `/${ROUTER_LINKS.ERROR}` ||
      location.pathname !== `/${ROUTER_LINKS.MAINTENANCE}`
    )
      sessionStorage.setItem('redirectPath', location.pathname);
    if (projectId) {
      window.location.href = `${environment.apiUrl}/login?project_id=${projectId}`;
    } else {
      window.location.href = `${environment.apiUrl}/login`;
    }
  }
}
