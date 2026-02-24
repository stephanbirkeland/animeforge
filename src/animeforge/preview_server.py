"""WebSocket live preview server for mock generation."""

from __future__ import annotations

import asyncio
import base64
import http.server
import json
import threading
import webbrowser
from pathlib import Path
from typing import Any

import websockets
import websockets.server

from animeforge.backend.base import GenerationRequest, ProgressCallback
from animeforge.backend.mock import MockBackend

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "preview.html"


class _HTMLHandler(http.server.BaseHTTPRequestHandler):
    """Serves the preview HTML page."""

    ws_port: int = 8766

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            html = _TEMPLATE_PATH.read_text()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            self.send_error(404)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass  # suppress console noise


class PreviewServer:
    """Runs an HTTP + WebSocket server for live generation preview."""

    def __init__(self, http_port: int = 8765, ws_port: int = 8766) -> None:
        self.http_port = http_port
        self.ws_port = ws_port
        self._clients: set[websockets.server.ServerConnection] = set()
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._http_server: http.server.HTTPServer | None = None

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a JSON message to all connected WebSocket clients."""
        data = json.dumps(message)
        websockets.broadcast(self._clients, data)

    def _make_progress_callback(self) -> ProgressCallback:
        """Return a sync callback that enqueues progress messages."""

        def callback(step: int, total: int, status: str) -> None:
            self._queue.put_nowait({
                "type": "progress",
                "step": step,
                "total": total,
                "status": status,
            })

        return callback

    async def _broadcast_loop(self) -> None:
        """Drain the queue and broadcast messages to clients."""
        while True:
            msg = await self._queue.get()
            await self.broadcast(msg)

    async def _ws_handler(self, websocket: websockets.server.ServerConnection) -> None:
        """Handle a single WebSocket connection."""
        self._clients.add(websocket)
        try:
            async for _message in websocket:
                pass  # we only send, never receive meaningful data
        finally:
            self._clients.discard(websocket)

    async def _run_generation(self, prompt: str) -> None:
        """Run mock generation and broadcast progress + result."""
        backend = MockBackend()
        await backend.connect()

        request = GenerationRequest(prompt=prompt, width=512, height=512)
        result = await backend.generate(request, progress_callback=self._make_progress_callback())

        if result.images:
            image_data = result.images[0].read_bytes()
            b64 = base64.b64encode(image_data).decode("ascii")
            self._queue.put_nowait({
                "type": "complete",
                "image": f"data:image/png;base64,{b64}",
            })

        await backend.disconnect()

    def _start_http_server(self) -> None:
        """Start the HTTP server in a daemon thread."""
        handler_class = type(
            "_BoundHTMLHandler",
            (_HTMLHandler,),
            {"ws_port": self.ws_port},
        )
        self._http_server = http.server.HTTPServer(
            ("", self.http_port), handler_class
        )
        thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        thread.start()

    async def run(self, prompt: str, open_browser: bool = True) -> None:
        """Start servers, run generation, and wait for shutdown."""
        self._start_http_server()

        broadcaster = None
        generation = None

        try:
            async with websockets.serve(self._ws_handler, "localhost", self.ws_port):
                if open_browser:
                    webbrowser.open(
                        f"http://localhost:{self.http_port}?ws={self.ws_port}"
                    )

                broadcaster = asyncio.create_task(self._broadcast_loop())
                generation = asyncio.create_task(self._run_generation(prompt))

                # Wait for generation to finish, then keep server alive
                await generation
                # Give a moment for the complete message to broadcast
                await asyncio.sleep(0.2)
                # Hold server open until cancelled (Ctrl+C)
                await asyncio.Future()
        finally:
            if broadcaster and not broadcaster.done():
                broadcaster.cancel()
            if generation and not generation.done():
                generation.cancel()
            if self._http_server:
                self._http_server.shutdown()
