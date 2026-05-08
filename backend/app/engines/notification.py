"""
Notification Engine
Simulates SMS and push notification delivery to emergency contacts.
"""
import asyncio
import random
import logging
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


class NotificationEngine:
    """
    Simulates notification delivery for demo purposes.
    In production, this would integrate with SMS gateways (Twilio, MSG91, etc.)
    """

    # Simulated delivery success rates
    SMS_SUCCESS_RATE = 0.95
    PUSH_SUCCESS_RATE = 0.90
    OFFLINE_QUEUE: list = []

    async def notify_emergency_contacts(
        self,
        contacts: list,
        incident_id: str,
        incident_location: str,
        severity: str,
        ambulance_eta: Optional[float] = None,
    ) -> List[dict]:
        """Send notifications to all emergency contacts."""
        results = []

        for contact in contacts:
            result = await self._send_sms(
                phone=contact.phone,
                name=contact.name,
                message=self._build_emergency_message(
                    incident_id, incident_location, severity, ambulance_eta
                ),
                incident_id=incident_id,
            )
            results.append(result)

        return results

    async def notify_dispatch_center(
        self,
        incident_id: str,
        severity: str,
        location: str,
        ambulance_id: Optional[str] = None,
        hospital_name: Optional[str] = None,
    ) -> dict:
        """Notify emergency dispatch center."""
        message = (
            f"[RoadSoS ALERT] Incident {incident_id} | Severity: {severity} | "
            f"Location: {location}"
        )
        if ambulance_id:
            message += f" | Ambulance: {ambulance_id}"
        if hospital_name:
            message += f" | Hospital: {hospital_name}"

        return await self._send_push_notification(
            channel="dispatch_center",
            title=f"🚨 {severity} Incident Detected",
            body=message,
            incident_id=incident_id,
        )

    async def notify_police(self, incident_id: str, location: str) -> dict:
        """Notify nearest police station (for CRITICAL incidents)."""
        return await self._send_push_notification(
            channel="police",
            title="🚔 Critical Road Accident",
            body=f"Critical accident at {location}. Incident ID: {incident_id}. Immediate response required.",
            incident_id=incident_id,
        )

    async def notify_fire_brigade(self, incident_id: str, location: str) -> dict:
        """Notify fire brigade (for CRITICAL incidents)."""
        return await self._send_push_notification(
            channel="fire_brigade",
            title="🚒 Critical Road Accident",
            body=f"Critical accident at {location}. Incident ID: {incident_id}. Fire/rescue may be required.",
            incident_id=incident_id,
        )

    async def _send_sms(
        self,
        phone: str,
        name: str,
        message: str,
        incident_id: str,
    ) -> dict:
        """Simulate SMS delivery."""
        # Simulate network delay
        await asyncio.sleep(random.uniform(0.1, 0.5))

        success = random.random() < self.SMS_SUCCESS_RATE
        status = "DELIVERED" if success else "FAILED"

        result = {
            "type": "SMS",
            "recipient": name,
            "phone": phone[-4:].rjust(len(phone), "*"),  # mask phone
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "incident_id": incident_id,
            "message_preview": message[:100] + "..." if len(message) > 100 else message,
        }

        if not success:
            # Queue for retry
            self.OFFLINE_QUEUE.append({
                "phone": phone,
                "message": message,
                "incident_id": incident_id,
                "queued_at": datetime.utcnow().isoformat(),
            })
            logger.warning(f"SMS delivery failed for {phone[-4:]}, queued for retry")
        else:
            logger.info(f"SMS delivered to {phone[-4:]} for incident {incident_id}")

        return result

    async def _send_push_notification(
        self,
        channel: str,
        title: str,
        body: str,
        incident_id: str,
    ) -> dict:
        """Simulate push notification delivery."""
        await asyncio.sleep(random.uniform(0.05, 0.2))

        success = random.random() < self.PUSH_SUCCESS_RATE

        return {
            "type": "PUSH",
            "channel": channel,
            "title": title,
            "status": "DELIVERED" if success else "FAILED",
            "timestamp": datetime.utcnow().isoformat(),
            "incident_id": incident_id,
        }

    def _build_emergency_message(
        self,
        incident_id: str,
        location: str,
        severity: str,
        ambulance_eta: Optional[float],
    ) -> str:
        """Build SMS message for emergency contacts."""
        msg = (
            f"🚨 ROADSOS EMERGENCY ALERT\n"
            f"Your contact has been in a road accident.\n"
            f"Severity: {severity}\n"
            f"Location: {location}\n"
            f"Incident ID: {incident_id}\n"
        )
        if ambulance_eta:
            msg += f"Ambulance ETA: {ambulance_eta:.0f} minutes\n"
        msg += "Emergency services have been notified. Track at roadsos.local"
        return msg

    async def retry_queued_notifications(self) -> int:
        """Retry failed notifications from the queue."""
        if not self.OFFLINE_QUEUE:
            return 0

        retried = 0
        failed_again = []

        for notification in self.OFFLINE_QUEUE:
            success = random.random() < self.SMS_SUCCESS_RATE
            if success:
                retried += 1
                logger.info(f"Retry successful for incident {notification['incident_id']}")
            else:
                failed_again.append(notification)

        self.OFFLINE_QUEUE = failed_again
        return retried


# Singleton instance
notification_engine = NotificationEngine()
