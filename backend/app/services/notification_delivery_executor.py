"""
Notification delivery executor that sends events through configured channels.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import httpx
from loguru import logger
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    NotificationChannelType,
    NotificationDelivery,
)
from app.domains.notifications.services import DispatcherService
from app.services.telegram_service import TelegramService


class NotificationDeliveryExecutor:
    """Dispatches notification deliveries across channels."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dispatcher = DispatcherService(db)
        self.telegram_service = TelegramService()

    async def process_delivery(self, delivery: NotificationDelivery) -> bool:
        """Process single delivery attempt."""
        channel = delivery.channel
        event = delivery.event
        payload = event.payload or {}

        try:
            if channel.channel_type == NotificationChannelType.TELEGRAM:
                return await self._send_telegram(delivery, payload)
            if channel.channel_type == NotificationChannelType.WEBHOOK:
                return await self._send_webhook(delivery, payload)
            if channel.channel_type in {NotificationChannelType.SLACK, NotificationChannelType.ZAPIER}:
                return await self._send_webhook(delivery, payload)
            if channel.channel_type == NotificationChannelType.EMAIL:
                return await self._send_email(delivery, payload)

            await self.dispatcher.mark_delivery_failed(
                delivery.id,
                error_message=f"Unsupported channel type {channel.channel_type}",
                retry_in_seconds=None,
            )
            return False
        except Exception as exc:
            logger.error("Delivery failed for %s due to %s", delivery.id, exc, exc_info=True)
            channel_config = delivery.channel.metadata_json or {}
            await self.dispatcher.mark_delivery_failed(
                delivery.id,
                error_message=str(exc),
                retry_in_seconds=channel_config.get("retry_seconds", 300),
            )
            return False

    async def _send_telegram(self, delivery: NotificationDelivery, payload: dict) -> bool:
        """Send notification via Telegram direct message."""
        chat_id = delivery.channel.destination
        title = payload.get("title", "Update")
        message = payload.get("message") or payload.get("summary") or ""

        success = await self.telegram_service.send_notification(chat_id, title, message)
        if success:
            await self.dispatcher.mark_delivery_sent(
                delivery.id,
                response_metadata={"channel": "telegram"},
            )
            return True

        await self.dispatcher.mark_delivery_failed(
            delivery.id,
            error_message="Telegram delivery failed",
            retry_in_seconds=payload.get("retry_seconds", 300),
        )
        return False

    async def _send_webhook(self, delivery: NotificationDelivery, payload: dict) -> bool:
        """Trigger webhook call with event payload."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(delivery.channel.destination, json=payload)
        if response.status_code < 300:
            await self.dispatcher.mark_delivery_sent(
                delivery.id,
                response_metadata={
                    "channel": "webhook",
                    "status_code": response.status_code,
                },
            )
            return True

        error_text = response.text[:200]
        channel_config = delivery.channel.metadata_json or {}
        await self.dispatcher.mark_delivery_failed(
            delivery.id,
            error_message=f"Webhook responded with {response.status_code}: {error_text}",
            retry_in_seconds=channel_config.get("retry_seconds", 300),
        )
        return False

    async def _send_email(self, delivery: NotificationDelivery, payload: dict) -> bool:
        """Send email using SendGrid when configured."""
        api_key = settings.SENDGRID_API_KEY
        if not api_key:
            await self.dispatcher.mark_delivery_failed(
                delivery.id,
                error_message="SendGrid API key not configured",
                retry_in_seconds=None,
                max_attempts=1,
            )
            return False

        subject = payload.get("title", "AI Competitor Insight Update")
        message = payload.get("message") or payload.get("summary") or ""
        html_content = payload.get("html") or f"<p>{message}</p>"

        mail = Mail(
            from_email=settings.FROM_EMAIL,
            to_emails=delivery.channel.destination,
            subject=subject,
            html_content=html_content,
        )

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            self._send_sendgrid_request,
            api_key,
            mail,
        )

        if response.status_code < 300:
            await self.dispatcher.mark_delivery_sent(
                delivery.id,
                response_metadata={
                    "channel": "email",
                    "status_code": response.status_code,
                },
            )
            return True

        channel_config = delivery.channel.metadata_json or {}
        await self.dispatcher.mark_delivery_failed(
            delivery.id,
            error_message=f"SendGrid responded with {response.status_code}",
            retry_in_seconds=channel_config.get("retry_seconds", 600),
        )
        return False

    @staticmethod
    def _send_sendgrid_request(api_key: str, mail: Mail):
        client = SendGridAPIClient(api_key)
        return client.send(mail)


