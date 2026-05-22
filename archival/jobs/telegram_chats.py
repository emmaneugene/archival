import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from archival.jobs.base import Job, JobResult, JobStatus

try:
    from telethon import TelegramClient
    from telethon.tl.types import (
        Channel,
        Chat,
        User,
        Message,
        MessageMediaPhoto,
        MessageMediaDocument,
        MessageMediaWebPage,
    )

    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False


def serialize_message(message: "Message") -> dict:
    """Convert a Telegram message to a JSON-serializable dictionary."""
    data = {
        "id": message.id,
        "date": message.date.isoformat() if message.date else None,
        "text": message.text or message.message or "",
        "out": message.out,
        "reply_to_msg_id": message.reply_to.reply_to_msg_id if message.reply_to else None,
        "edit_date": message.edit_date.isoformat() if message.edit_date else None,
        "forwards": message.forwards,
        "views": message.views,
    }

    if message.sender:
        sender = message.sender
        if isinstance(sender, User):
            data["sender"] = {
                "type": "user",
                "id": sender.id,
                "first_name": sender.first_name,
                "last_name": sender.last_name,
                "username": sender.username,
                "phone": sender.phone,
            }
        elif isinstance(sender, (Channel, Chat)):
            data["sender"] = {
                "type": "channel" if isinstance(sender, Channel) else "chat",
                "id": sender.id,
                "title": sender.title,
                "username": getattr(sender, "username", None),
            }
    else:
        data["sender"] = None

    if message.media:
        if isinstance(message.media, MessageMediaPhoto):
            data["media"] = {"type": "photo"}
        elif isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            mime_type = doc.mime_type if doc else None
            data["media"] = {
                "type": "document",
                "mime_type": mime_type,
                "size": doc.size if doc else None,
            }
        elif isinstance(message.media, MessageMediaWebPage):
            webpage = message.media.webpage
            if hasattr(webpage, "url"):
                data["media"] = {
                    "type": "webpage",
                    "url": webpage.url,
                    "title": getattr(webpage, "title", None),
                    "description": getattr(webpage, "description", None),
                }
            else:
                data["media"] = {"type": "webpage"}
        else:
            data["media"] = {"type": type(message.media).__name__}
    else:
        data["media"] = None

    return data


def serialize_chat(dialog) -> dict:
    """Convert a Telegram dialog/chat to a JSON-serializable dictionary."""
    entity = dialog.entity

    chat_type = "unknown"
    if isinstance(entity, User):
        chat_type = "user"
    elif isinstance(entity, Channel):
        chat_type = "channel" if entity.broadcast else "supergroup"
    elif isinstance(entity, Chat):
        chat_type = "group"

    return {
        "id": entity.id,
        "type": chat_type,
        "name": dialog.name,
        "username": getattr(entity, "username", None),
        "unread_count": dialog.unread_count,
        "last_message_date": dialog.date.isoformat() if dialog.date else None,
    }


class TelegramJob(Job):
    name = "telegram"
    description = "Archive Telegram chats and messages"

    def __init__(self, data_dir: Path, config_dir: Path):
        super().__init__(data_dir, config_dir)
        self.session_dir = self.data_dir / "telegram" / "sessions"
        self.output_dir = self.data_dir / "telegram" / "exports"

    def _get_credentials(self) -> tuple[str, str]:
        """Get Telegram API credentials from config or environment."""
        api_id = os.environ.get("TELEGRAM_API_ID")
        api_hash = os.environ.get("TELEGRAM_API_HASH")

        if not api_id or not api_hash:
            env_file = self.config_dir / ".env"
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key == "TELEGRAM_API_ID":
                                api_id = value
                            elif key == "TELEGRAM_API_HASH":
                                api_hash = value

        if not api_id or not api_hash:
            raise ValueError(
                "Telegram API credentials not found. "
                "Set TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables, "
                "or create config/.env"
            )

        return api_id, api_hash

    async def _list_chats(self, client: "TelegramClient", limit: int = 100) -> list[dict]:
        """List all available chats/dialogs."""
        dialogs = await client.get_dialogs(limit=limit)
        return [serialize_chat(d) for d in dialogs]

    async def _fetch_messages(
        self,
        client: "TelegramClient",
        chat_identifier: str | int,
        limit: Optional[int] = None,
        offset_date: Optional[datetime] = None,
    ) -> tuple[dict, list[dict]]:
        """Fetch messages from a specific chat."""
        entity = await client.get_entity(chat_identifier)

        chat_info = {
            "id": entity.id,
            "type": type(entity).__name__.lower(),
            "name": getattr(entity, "title", None)
            or getattr(entity, "first_name", None)
            or str(entity.id),
            "username": getattr(entity, "username", None),
        }

        messages = []
        async for message in client.iter_messages(
            entity,
            limit=limit,
            offset_date=offset_date,
        ):
            if isinstance(message, Message):
                messages.append(serialize_message(message))

        return chat_info, messages

    async def _run_async(
        self,
        chat: Optional[str] = None,
        chat_id: Optional[int] = None,
        limit: Optional[int] = None,
        list_chats: bool = False,
    ) -> JobResult:
        """Async implementation of the job."""
        if not TELETHON_AVAILABLE:
            return JobResult(
                status=JobStatus.FAILURE,
                message="Telethon library not installed. Run: pip install telethon",
            )

        try:
            api_id, api_hash = self._get_credentials()
        except ValueError as e:
            return JobResult(status=JobStatus.FAILURE, message=str(e))

        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        session_path = self.session_dir / "telegram_archival"
        client = TelegramClient(str(session_path), api_id, api_hash)

        try:
            await client.start()

            if list_chats:
                chats = await self._list_chats(client)
                output_path = self.output_dir / f"chats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(chats, f, ensure_ascii=False, indent=2)

                return JobResult(
                    status=JobStatus.SUCCESS,
                    message=f"Listed {len(chats)} chats. Output: {output_path}",
                    metadata={"chat_count": len(chats), "output_path": str(output_path)},
                )

            chat_identifier = chat_id if chat_id else chat
            if not chat_identifier:
                return JobResult(
                    status=JobStatus.FAILURE,
                    message="No chat specified. Use --chat or --chat-id option, or --list-chats to see available chats.",
                )

            chat_info, messages = await self._fetch_messages(
                client, chat_identifier, limit=limit
            )

            safe_name = "".join(
                c if c.isalnum() or c in "-_" else "_" for c in chat_info["name"]
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"{safe_name}_{timestamp}.json"

            output_data = {
                "export_date": datetime.now().isoformat(),
                "chat": chat_info,
                "message_count": len(messages),
                "messages": messages,
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            return JobResult(
                status=JobStatus.SUCCESS,
                message=f"Archived {len(messages)} messages from '{chat_info['name']}'. Output: {output_path}",
                metadata={
                    "chat": chat_info,
                    "message_count": len(messages),
                    "output_path": str(output_path),
                },
            )

        except Exception as e:
            return JobResult(status=JobStatus.FAILURE, message=str(e))
        finally:
            await client.disconnect()

    def run(
        self,
        chat: Optional[str] = None,
        chat_id: Optional[int] = None,
        limit: Optional[int] = None,
        list_chats: bool = False,
    ) -> JobResult:
        """Execute the Telegram archival job."""
        return asyncio.run(
            self._run_async(chat=chat, chat_id=chat_id, limit=limit, list_chats=list_chats)
        )
