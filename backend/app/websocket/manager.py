"""
WebSocket Connection Manager
Handles real-time broadcasting to all connected dashboard clients.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id} (total: {len(self.active_connections)})")

    async def disconnect(self, client_id: str):
        """Remove a disconnected client."""
        async with self._lock:
            self.active_connections.pop(client_id, None)
        logger.info(f"WebSocket client disconnected: {client_id} (total: {len(self.active_connections)})")

    async def send_to_client(self, client_id: str, message: dict):
        """Send a message to a specific client."""
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.warning(f"Failed to send to client {client_id}: {e}")
                await self.disconnect(client_id)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        message_str = json.dumps(message, default=str)
        disconnected = []

        for client_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.warning(f"Broadcast failed for client {client_id}: {e}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)

    async def broadcast_event(self, event_type: str, payload: dict, channel: str = "general"):
        """Broadcast a typed event with standard schema."""
        message = {
            "type": event_type,
            "channel": channel,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(message)

    async def send_state_snapshot(self, client_id: str, snapshot: dict):
        """Send current state snapshot to a newly connected client."""
        message = {
            "type": "STATE_SNAPSHOT",
            "channel": "general",
            "payload": snapshot,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.send_to_client(client_id, message)

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


# Event type constants
class WSEventType:
    # Incidents
    INCIDENT_CREATED = "INCIDENT_CREATED"
    INCIDENT_UPDATED = "INCIDENT_UPDATED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"

    # Ambulances
    AMBULANCE_POSITION_UPDATE = "AMBULANCE_POSITION_UPDATE"
    AMBULANCE_STATUS_CHANGE = "AMBULANCE_STATUS_CHANGE"
    AMBULANCE_ASSIGNED = "AMBULANCE_ASSIGNED"

    # Hospitals
    HOSPITAL_STATUS_UPDATE = "HOSPITAL_STATUS_UPDATE"
    HOSPITAL_RANKING_UPDATE = "HOSPITAL_RANKING_UPDATE"

    # Risk
    RISK_ZONE_UPDATE = "RISK_ZONE_UPDATE"
    HEATMAP_UPDATE = "HEATMAP_UPDATE"

    # Notifications
    NOTIFICATION_SENT = "NOTIFICATION_SENT"
    EMERGENCY_ALERT = "EMERGENCY_ALERT"

    # Hardware Telemetry
    HARDWARE_TELEMETRY = "HARDWARE_TELEMETRY"

    # System
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    HEARTBEAT = "HEARTBEAT"
    DEMO_EVENT = "DEMO_EVENT"


# Global manager instance
ws_manager = ConnectionManager()
