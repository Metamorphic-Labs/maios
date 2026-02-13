# tests/integration/test_websocket.py
import pytest
from starlette.testclient import TestClient


def test_websocket_connection():
    """Test WebSocket connection."""
    from maios.api.main import app

    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send a ping
        websocket.send_json({"type": "ping"})
        # Receive response
        data = websocket.receive_json()
        assert data["type"] == "pong"
