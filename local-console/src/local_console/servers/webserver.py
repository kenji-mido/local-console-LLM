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
import threading
from abc import ABC
from abc import abstractmethod
from collections.abc import AsyncGenerator
from collections.abc import Awaitable
from collections.abc import Sequence
from pathlib import Path
from pathlib import PurePosixPath
from types import TracebackType
from typing import Any
from typing import Callable
from typing import Optional
from typing import Self

import trio
from local_console.core.config import Config
from local_console.core.files.files import file_hash
from local_console.core.schemas.schemas import DeviceID
from local_console.utils.singleton import Singleton

logger = logging.getLogger(__name__)


FileIncomingFn = Callable[[bytes, str], None]
FileIncomingAsyncFn = Callable[[bytes, str], Awaitable[None]]


def get_range(range_header: str, file_size: int) -> tuple[int, int]:
    unit, byte_range = range_header.split("=")
    assert unit == "bytes"

    start, end = (int(x) if x else None for x in byte_range.split("-"))
    start = start or 0
    end = min(end or file_size - 1, file_size - 1)
    return start, end


class URLMap(metaclass=Singleton):
    """
    A singleton class for managing URL -> file path mappings in a thread-safe manner.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._map: dict[str, Path] = {}

    def get(self, url_path: str) -> Path | None:
        """
        Retrieve the file path for a given url_path, or None if not found.
        """
        with self._lock:
            return self._map.get(url_path)

    def add(self, url_path: str, file_path: Path) -> None:
        """
        Add or update a mapping from url_path to file_path.
        """
        with self._lock:
            self._map[url_path] = file_path

    def forget(self, url_path: str) -> None:
        """
        Remove an entry in the mapping
        """
        with self._lock:
            del self._map[url_path]


class LocalConsoleRequestsHandler(http.server.BaseHTTPRequestHandler):

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

    def do_GET(self) -> None:
        url_map = URLMap()  # The map is a singleton

        file_path = url_map.get(self.path)
        if file_path is None or not file_path.exists():
            self.send_error(404, "File Not Found")
            return

        file_size = file_path.stat().st_size
        header_range = self.headers.get("Range")
        logger.debug(f"Header range: {header_range}")

        with file_path.open("rb") as f:
            if header_range:
                # https://www.rfc-editor.org/rfc/rfc9110.html#name-range-requests
                try:
                    start, end = get_range(header_range, file_size)
                    content_range = f"bytes {start}-{end}/{file_size}"

                    logger.debug(f"Content range: {content_range}")
                    if start > end or start >= file_size:
                        self.send_error(416, "Range Not Satisfiable")
                        return
                    f.seek(start)
                    data = f.read(end - start + 1)
                    content_range = f"bytes {start}-{end}/{file_size}"
                    # Partial Content
                    self.send_response(206)
                    self.send_header("Content-Range", content_range)
                    self.send_header("Accept-Ranges", "bytes")
                except ValueError:
                    self.send_error(416, "Range Not Satisfiable")
                    return
            else:
                data = f.read()
                self.send_response(200)

        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(data)

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

    def __init__(self, port: int) -> None:
        self.port = port
        self.thread: threading.Thread | None = None

    @abstractmethod
    def handler(self, *args: Any, **kwargs: Any) -> http.server.BaseHTTPRequestHandler:
        "Must return an specialization of BaseHTTPRequestHandler"

    def start(self) -> None:
        self.thread, self.server = self._setup_threads()
        self.thread.start()

        # In case the `self.port == 0`, it gets updated with the
        # port allocated by the OS after `start()`
        self.port = self.server.server_port
        logger.debug("Serving at port %d", self.port)

    def _setup_threads(
        self,
    ) -> tuple[threading.Thread, http.server.ThreadingHTTPServer]:
        # This is a method, just to simplify mocking

        # Create the server object
        server = http.server.ThreadingHTTPServer(("0.0.0.0", self.port), self.handler)

        # Start the server in a new thread
        main_thread = threading.Thread(
            target=server.serve_forever, name=f"Webserver_{self.port}"
        )

        return main_thread, server

    def is_running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def stop(self) -> None:
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
        port: int = 0,
        on_incoming: Optional[FileIncomingFn] = None,
        max_upload_size: Optional[int] = None,
    ) -> None:
        super().__init__(port)
        self.on_incoming = on_incoming
        self.max_upload_size = max_upload_size

    def handler(self, *args: Any, **kwargs: Any) -> LocalConsoleRequestsHandler:
        return LocalConsoleRequestsHandler(
            *args,
            on_incoming=self.on_incoming,
            max_upload_size=self.max_upload_size,
            **kwargs,
        )

    def enlist_file(self, target_file: Path) -> str:
        """
        Make a file available for GET at deterministic URL.
        """
        url = SyncWebserver.url_path_for(target_file)
        URLMap().add(url, target_file)
        return url

    def delist_file(self, target_file: Path) -> None:
        """
        Stop a file from being available for GET.
        """
        url = SyncWebserver.url_path_for(target_file)
        URLMap().forget(url)

    @staticmethod
    def url_path_for(target_file: Path) -> str:
        prefix = file_hash(target_file.read_bytes())[:12]
        url = f"/{prefix}/{target_file.name}"
        return url

    def url_root_at(self, device_id: DeviceID) -> str:
        """
        For reference on URL components, see:
        https://developer.mozilla.org/en-US/docs/Learn_web_development/Howto/Web_mechanics/What_is_a_URL

        Computes the URL authority component for this server instance,
        which should already be `.start()`ed (so that the port in the
        authority component of the URL is already bound).

        Uses the fixed 'http' scheme as this server implementation does
        not support TLS.

        The host is determined based on the global configuration: if
        it is left at its default, then the host address determined for
        the MQTT broker is used; otherwise, the non-default address is
        used.
        """
        assert self.is_running()

        webparams = Config().data.config.webserver
        device_conf = Config().get_device_config(device_id)

        host_address = (
            device_conf.mqtt.host if webparams.host == "0.0.0.0" else webparams.host
        )
        root = f"http://{host_address}:{self.port}/"
        return root


class AsyncWebserver(SyncWebserver):
    """
    This class wraps the synchronous context manager methods
    from SyncWebserver, as they are not really blocking. This
    enables managing the webserver from async contexts.

    This makes use of a channel for quickly switching processing
    of incoming payloads from the internal sync context
    (of the base SyncWebserver) back to the calling async context.
    """

    def __init__(
        self,
        port: int = 0,
        max_upload_size: Optional[int] = None,
    ) -> None:
        super().__init__(port, self._to_async, max_upload_size)

        chparts: tuple[
            trio.MemorySendChannel[tuple[bytes, str]],
            trio.MemoryReceiveChannel[tuple[bytes, str]],
        ] = trio.open_memory_channel(0)
        self._recv_channel, self._proc_channel = chparts
        self._trio_token = trio.lowlevel.current_trio_token()

    def _to_async(self, data: bytes, url_path: str) -> None:
        # Push the received data to the async side via the channel
        trio.from_thread.run(
            self._recv_channel.send,
            (data, url_path),
            trio_token=self._trio_token,
        )

    async def receive(self) -> AsyncGenerator[tuple[bytes, str], None]:
        async with (
            self._recv_channel,
            self._proc_channel,
        ):
            # Receive uploaded files over the memory channel
            async for data, url_path in self._proc_channel:
                yield data, url_path

    async def __aenter__(self) -> Self:
        self.__enter__()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        return self.__exit__(exc_type, exc_val, exc_tb)


def combine_url_components(root: str, *parts: str) -> str:
    no_trailing_slashes = (p.strip("/") for p in parts)
    all_parts = [root.rstrip("/"), *no_trailing_slashes]
    return "/".join(all_parts)


class FileInbox:
    """
    Uses an internal mapping to invoke dynamically assigned,
    per-device processing functions for incoming blobs. This
    enables sharing blob processing for multiple cameras with
    a single webserver instance.
    """

    def __init__(
        self,
        webserver: AsyncWebserver,
    ):
        self.webserver = webserver
        self._map: dict[DeviceID, FileIncomingAsyncFn] = {}

    def set_file_incoming_callable(
        self, device_id: DeviceID, afunc: FileIncomingAsyncFn
    ) -> str:
        assert (
            device_id not in self._map
        ), f"Device ID {device_id} already has a registered blob function."
        self._map[device_id] = afunc

        url_root = self.webserver.url_root_at(device_id)
        upload_url = f"{url_root}{device_id}"
        return upload_url

    def reset_file_incoming_callable(self, device_id: DeviceID) -> None:
        if device_id in self._map:
            del self._map[device_id]

    async def blobs_dispatch_task(
        self, *, task_status: Any = trio.TASK_STATUS_IGNORED
    ) -> None:
        assert self.webserver.is_running()

        task_status.started()
        async for data, url_path in self.webserver.receive():
            await self.dispatch_blob(PurePosixPath(url_path), data)

    async def dispatch_blob(self, url_path: PurePosixPath, data: bytes) -> None:
        assert url_path.parts[0] == "/"
        anchor = url_path.parts[1]
        try:
            device_id = DeviceID(int(anchor))
        except ValueError:
            logger.warning(f"Received blob at path {url_path} without a target prefix.")
            return

        if device_id in self._map:
            await self._map[device_id](data, str(url_path))
        else:
            logger.warning(
                f"Received blob at path {url_path} which has no function registered."
            )
