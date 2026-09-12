from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
import httpx


@dataclass
class PublishResult:
    success: bool
    detail: str
    external_post_id: str | None = None


class SocialPublisher(ABC):

    @abstractmethod
    def publish(self, variant, idempotency_key: str) -> PublishResult:
        pass
    

class MockXPublisher(SocialPublisher):

    def publish(self, variant, idempotency_key: str) -> PublishResult:
        return PublishResult(
            success=True,
            detail="Mock X post published",
            external_post_id=f"mock-x-{variant.id}"
        )
        
        
class MockLinkedInPublisher(SocialPublisher):

    def publish(self, variant, idempotency_key: str) -> PublishResult:
        return PublishResult(
            success=True,
            detail="Mock LinkedIn post published",
            external_post_id=f"mock-linkedin-{variant.id}"
        )
        
        
        
class TelegramPublisher(SocialPublisher):

    def publish(self, variant, idempotency_key: str) -> PublishResult:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not bot_token or not chat_id:
            return PublishResult(
                success=False,
                detail="Telegram credentials are not configured"
            )

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        try:
            response = httpx.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": variant.content
                },
                timeout=10
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return PublishResult(
                success=False,
                detail="Telegram publish failed"
            )

        data = response.json()

        return PublishResult(
            success=True,
            detail="Telegram post published",
            external_post_id=str(data["result"]["message_id"])
        )