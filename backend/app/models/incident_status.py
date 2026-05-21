"""
Incident State Machine — Explicit, validated status transitions.
"""
import enum
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class IncidentStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    DISPATCHING = "DISPATCHING"
    EN_ROUTE_TO_SCENE = "EN_ROUTE_TO_SCENE"
    ON_SCENE = "ON_SCENE"
    TRANSPORTING = "TRANSPORTING"
    AT_HOSPITAL = "AT_HOSPITAL"
    RESOLVED = "RESOLVED"
    FALSE_ALARM = "FALSE_ALARM"

    # Valid transitions: current_status → set of allowed next statuses
    _transitions = {
        DETECTED: {DISPATCHING, FALSE_ALARM},
        DISPATCHING: {EN_ROUTE_TO_SCENE, FALSE_ALARM},
        EN_ROUTE_TO_SCENE: {ON_SCENE, RESOLVED, FALSE_ALARM},
        ON_SCENE: {TRANSPORTING, RESOLVED, FALSE_ALARM},
        TRANSPORTING: {AT_HOSPITAL, RESOLVED},
        AT_HOSPITAL: {RESOLVED},
        RESOLVED: set(),
        FALSE_ALARM: set(),
    }

    @classmethod
    def is_valid_transition(cls, current: str, next_status: str) -> bool:
        """Check if a status transition is valid according to the state machine."""
        try:
            cur = cls(current.upper())
            nxt = cls(next_status.upper())
            return nxt in cls._transitions.value[cur]
        except (ValueError, KeyError):
            return False

    @classmethod
    def validate_transition(cls, current: str, next_status: str) -> Optional[str]:
        """Validate transition, returning error message or None if valid."""
        try:
            cur = cls(current.upper())
            nxt = cls(next_status.upper())
        except ValueError:
            return f"Invalid status value: '{current}' or '{next_status}'"

        if nxt in cls._transitions.value[cur]:
            return None
        else:
            allowed = ", ".join(s.value for s in cls._transitions.value[cur])
            return f"Invalid transition: {current} → {next_status}. Allowed: [{allowed}]"


# List of all statuses ordered from initial to terminal
INCIDENT_STATUS_ORDER = [
    IncidentStatus.DETECTED,
    IncidentStatus.DISPATCHING,
    IncidentStatus.EN_ROUTE_TO_SCENE,
    IncidentStatus.ON_SCENE,
    IncidentStatus.TRANSPORTING,
    IncidentStatus.AT_HOSPITAL,
    IncidentStatus.RESOLVED,
]