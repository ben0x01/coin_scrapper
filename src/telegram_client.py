import asyncio
import logging

from telethon import TelegramClient
from telethon.errors import RPCError
from typing import Optional, List


class Telegram:
    def __init__(self, api_id: int, api_hash: str, session_name: str = 'session') -> None:
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    async def _connect_client(self) -> None:
        if not self.client.is_connected():
            await self.client.connect()

    async def _get_existing_messages(self, channel_id: int, limit: int = 2) -> List[str]:
        existing_messages = []
        async for message in self.client.iter_messages(channel_id, limit=limit):
            existing_messages.append(message.text)
        return existing_messages

    async def send_telegram_message(self, message: str, base_token_contract: str, channel_id: int) -> Optional[int]:
        await self._connect_client()

        try:
            existing_messages = await self._get_existing_messages(channel_id)

            if any(base_token_contract in msg for msg in existing_messages):
                self.logger.info("Message already sent for contract: %s", base_token_contract)
                return None

            self.logger.info("Sending message to channel %d: %s", channel_id, message)
            sent_message = await self.client.send_message(
                channel_id, message, parse_mode='HTML', link_preview=False
            )
            await asyncio.sleep(1)
            return sent_message.id
        except RPCError as e:
            self.logger.error("Failed to send message: %s", e)
            return None

    async def update_telegram_message(self, message_id: Optional[int], message: str, channel_id: int) -> None:
        await self._connect_client()

        try:
            self.logger.info("Updating message %d in channel %d", message_id, channel_id)
            await self.client.edit_message(channel_id, message_id, message, parse_mode='HTML', link_preview=False)
        except RPCError as e:
            self.logger.error("Failed to update message: %s", e)
