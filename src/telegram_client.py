import asyncio
import logging
from telethon import TelegramClient
from telethon.errors import RPCError


class Telegram:
    def __init__(self, api_id: int, api_hash: str, session_name: str = 'session') -> None:
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    async def sign_in(self) -> None:
        await self.client.connect()

        if not await self.client.is_user_authorized():
            print("You are not signed in. Please enter your phone number to continue:")
            phone_number = input("Phone number (with country code, e.g., +1234567890): ")
            try:
                await self.client.send_code_request(phone_number)
                print("Enter the verification code sent to your phone:")
                code = input("Code: ")
                try:
                    await self.client.sign_in(phone=phone_number, code=code)
                    print("Sign-in successful!")
                except Exception as e:
                    self.logger.error("Failed to sign in: %s", e)
                    print("Sign-in failed. Please try again.")
            except Exception as e:
                self.logger.error("Failed to send verification code: %s", e)
                print("Could not send verification code. Please check your phone number.")
        else:
            print("You are already signed in.")

    async def _connect_client(self) -> None:
        if not self.client.is_connected():
            await self.client.connect()

    async def _get_existing_messages(self, channel_id: int, limit: int = 2) -> list[str]:
        existing_messages = []
        async for message in self.client.iter_messages(channel_id, limit=limit):
            existing_messages.append(message.text)
        return existing_messages

    async def send_telegram_message(self, message: str, base_token_contract: str, channel_id: int) -> int | None:
        await self._connect_client()

        try:
            existing_messages = await self._get_existing_messages(channel_id)
            if any(base_token_contract in (msg or "") for msg in existing_messages):
                self.logger.info("Message already sent for contract: %s", base_token_contract)
                return None

            self.logger.info("Sending message to channel ID %d: %s", channel_id, message)
            sent_message = await self.client.send_message(
                channel_id, message, parse_mode='HTML', link_preview=False
            )
            await asyncio.sleep(1)
            return sent_message.id
        except RPCError as e:
            self.logger.error("Failed to send message: %s", e)
            return None

    async def update_telegram_message(self, message_id: int | None, message: str, channel_id: int) -> None:
        await self._connect_client()

        try:
            self.logger.info("Updating message ID %d in channel ID %d", message_id, channel_id)
            await self.client.edit_message(channel_id, message_id, message, parse_mode='HTML', link_preview=False)
        except RPCError as e:
            self.logger.error("Failed to update message: %s", e)

