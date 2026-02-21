"""
WebSocket-based log streamer.
Captures Python log records and broadcasts them to connected WebSocket clients.
"""
import logging
import asyncio
import json
from datetime import datetime, timezone
from typing import Set
from fastapi import WebSocket

# Connected WebSocket clients
_clients: Set[WebSocket] = set()
_log_buffer: list = []          # ring-buffer of recent log lines
_BUFFER_MAX = 500               # keep last 500 lines for new connections


class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that pushes records to all connected WebSocket clients."""

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
            }
            _log_buffer.append(entry)
            # Trim buffer
            while len(_log_buffer) > _BUFFER_MAX:
                _log_buffer.pop(0)

            # Schedule broadcast (fire-and-forget into the running event loop)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_broadcast(entry))
            except RuntimeError:
                pass  # no event loop yet – skip (startup logs before uvicorn)
        except Exception:
            self.handleError(record)


async def _broadcast(entry: dict):
    """Send a log entry to every connected client."""
    global _clients
    if not _clients:
        return
    payload = json.dumps(entry)
    dead: Set[WebSocket] = set()
    for ws in _clients.copy():
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


async def register(ws: WebSocket):
    """Accept a WebSocket and register it; replay the buffer first."""
    await ws.accept()
    _clients.add(ws)
    # Send buffered history so the client sees recent logs immediately
    for entry in _log_buffer:
        try:
            await ws.send_text(json.dumps(entry))
        except Exception:
            break


def unregister(ws: WebSocket):
    _clients.discard(ws)


def install_handler():
    """Attach the WebSocket handler to the root logger so it captures everything."""
    handler = WebSocketLogHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
