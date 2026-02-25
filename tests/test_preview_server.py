"""Tests for the WebSocket live preview server."""

import asyncio
import json
import threading
import urllib.request

import pytest
import websockets

from animeforge.preview_server import PreviewServer


@pytest.fixture
def server():
    """Create a PreviewServer with test ports."""
    return PreviewServer(http_port=0, ws_port=0)


class TestProgressCallback:
    """Tests for the progress callback factory."""

    def test_progress_callback_queues_message(self, server):
        callback = server._make_progress_callback()
        callback(3, 10, "generating step 3")
        msg = server._queue.get_nowait()
        assert msg == {
            "type": "progress",
            "step": 3,
            "total": 10,
            "status": "generating step 3",
        }

    def test_progress_callback_queues_multiple(self, server):
        callback = server._make_progress_callback()
        callback(1, 10, "step 1")
        callback(2, 10, "step 2")
        assert server._queue.qsize() == 2


class TestHTTPHandler:
    """Tests for the HTTP server serving preview.html."""

    def test_http_serves_html(self, server):
        server._start_http_server()
        try:
            port = server._http_server.server_address[1]
            with urllib.request.urlopen(f"http://localhost:{port}") as resp:
                body = resp.read().decode()
                assert resp.status == 200
                assert "<canvas" in body
                assert "AnimeForge Preview" in body
        finally:
            server._http_server.shutdown()

    def test_http_404_for_other_paths(self, server):
        server._start_http_server()
        try:
            port = server._http_server.server_address[1]
            try:
                urllib.request.urlopen(f"http://localhost:{port}/nonexistent")
                pytest.fail("Expected HTTPError")
            except urllib.error.HTTPError as e:
                assert e.code == 404
        finally:
            server._http_server.shutdown()


class TestWebSocketBroadcast:
    """Tests for WebSocket broadcast functionality."""

    @pytest.mark.asyncio
    async def test_broadcast_delivers_to_client(self):
        server = PreviewServer(http_port=0, ws_port=0)

        async with websockets.serve(server._ws_handler, "localhost", 0) as ws_server:
            port = ws_server.sockets[0].getsockname()[1]
            async with websockets.connect(f"ws://localhost:{port}") as client:
                # Small delay to let handler register the client
                await asyncio.sleep(0.05)
                await server.broadcast({"type": "progress", "step": 1, "total": 10, "status": "test"})
                raw = await asyncio.wait_for(client.recv(), timeout=2.0)
                msg = json.loads(raw)
                assert msg["type"] == "progress"
                assert msg["step"] == 1


class TestFullGenerationFlow:
    """Tests for end-to-end generation through the preview server."""

    @pytest.mark.asyncio
    async def test_generation_streams_progress_and_complete(self):
        server = PreviewServer(http_port=0, ws_port=0)

        async with websockets.serve(server._ws_handler, "localhost", 0) as ws_server:
            port = ws_server.sockets[0].getsockname()[1]
            async with websockets.connect(f"ws://localhost:{port}") as client:
                await asyncio.sleep(0.05)

                broadcaster = asyncio.create_task(server._broadcast_loop())
                generation = asyncio.create_task(server._run_generation("test prompt"))

                messages = []
                try:
                    while True:
                        raw = await asyncio.wait_for(client.recv(), timeout=5.0)
                        msg = json.loads(raw)
                        messages.append(msg)
                        if msg["type"] == "complete":
                            break
                finally:
                    broadcaster.cancel()
                    if not generation.done():
                        generation.cancel()

                progress_msgs = [m for m in messages if m["type"] == "progress"]
                complete_msgs = [m for m in messages if m["type"] == "complete"]

                assert len(progress_msgs) == 10
                steps = [m["step"] for m in progress_msgs]
                assert steps == list(range(1, 11))
                assert all(m["total"] == 10 for m in progress_msgs)

                assert len(complete_msgs) == 1
                assert complete_msgs[0]["image"].startswith("data:image/png;base64,")
