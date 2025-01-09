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
import http.server
import logging
import socketserver
import threading
from abc import ABC
from abc import abstractmethod
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import Any
from typing import Callable
from typing import Optional


logger = logging.getLogger(__name__)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


FileIncomingFn = Callable[[bytes, str], None]


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args: Any,
        on_incoming: Optional[FileIncomingFn] = None,
        max_upload_size: Optional[int] = None,
        **kwargs: Any,
    ):
        self.on_incoming = on_incoming
        self.max_upload_size = max_upload_size
        super().__init__(*args, **kwargs)

    def log_message(self, _format: str, *args: Sequence[str]) -> None:
        logger.debug(" ".join(str(arg) for arg in args))

    def do_PUT(self) -> None:
        response_code: int = 200
        response_msg: Optional[str] = None

        data: Optional[bytes] = None
        try:
            content_length = int(self.headers["Content-Length"])
            if (
                self.max_upload_size is not None
                and content_length > self.max_upload_size
            ):
                raise BufferError(content_length)
            data = self.rfile.read(content_length)

            # Notify of new file when the callback is set
            if data and self.on_incoming:
                try:
                    self.on_incoming(data, self.path)
                except Exception as e:
                    logger.error("Error while invoking callback", exc_info=e)

            response_code = 200

        except BufferError as e:
            response_msg = f"Upload size {content_length} bytes is greater than {self.max_upload_size} bytes, which is not allowed."
            logger.error(response_msg, exc_info=e)
            # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/413
            response_code = 413

        except Exception as e:
            logger.error("Error while receiving data", exc_info=e)
        finally:
            self.send_response(response_code, response_msg)
            self.end_headers()

    do_POST = do_PUT


class GenericWebserver(ABC):
    """
    This class connects an HTTP server class such as the one
    defined above, with an HTTP handler class, into a convenient
    context manager. The handler class must be returned from
    the handler() method, to be implemented.
    """

    def __init__(self, port: int, deploy: bool = True) -> None:
        self.port = port
        self.deploy = deploy

    @abstractmethod
    def handler(self, *args: Any, **kwargs: Any) -> http.server.BaseHTTPRequestHandler:
        "Must return an specialization of BaseHTTPRequestHandler"

    def start(self) -> None:
        if self.deploy:
            # Create the server object
            self.server = ThreadedHTTPServer(("0.0.0.0", self.port), self.handler)

            # Start the server in a new thread
            self.thread = threading.Thread(
                target=self.server.serve_forever, name=f"Webserver_{self.port}"
            )
            self.thread.start()

            self.port = self.server.server_port
            logger.debug("Serving at port %d", self.port)

    def stop(self) -> None:
        if not self.deploy:
            return

        logger.debug("Closing webserver at port %d", self.port)
        # Shutdown the server after exiting the context
        self.server.shutdown()
        self.server.server_close()

    def __enter__(self) -> "GenericWebserver":
        self.start()
        return self

    def __exit__(
        self,
        _exc_type: Optional[type[BaseException]],
        _exc_val: Optional[BaseException],
        _exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()


class SyncWebserver(GenericWebserver):
    """
    This class applies the generic webserver class above for providing
    the HTTP file server required in deployment workflows.
    """

    def __init__(
        self,
        directory: Path,
        port: int = 0,
        on_incoming: Optional[FileIncomingFn] = None,
        deploy: bool = True,
        max_upload_size: Optional[int] = None,
    ) -> None:
        super().__init__(port, deploy)
        self.dir = directory
        self.on_incoming = on_incoming
        self.max_upload_size = max_upload_size

    def handler(self, *args: Any, **kwargs: Any) -> CustomHTTPRequestHandler:
        return CustomHTTPRequestHandler(
            *args,
            directory=str(self.dir),
            on_incoming=self.on_incoming,
            max_upload_size=self.max_upload_size,
            **kwargs,
        )

    def set_directory(self, directory: Path) -> None:
        assert directory.is_dir()
        self.dir = directory


class AsyncWebserver(SyncWebserver):
    """
    This class wraps the synchronous context manager methods
    from SyncWebserver, as they are not really blocking. This
    enables managing the webserver from async contexts.
    """

    async def __aenter__(self) -> "GenericWebserver":
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        return self.__exit__(exc_type, exc_val, exc_tb)
