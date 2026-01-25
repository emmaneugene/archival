#!/usr/bin/env python3
"""
Telegram Message Fetcher

Fetches messages from personal Telegram channels and chats using the Telethon library.
Exports messages to JSON format for archival purposes.

Usage:
    1. Get API credentials from https://my.telegram.org
    2. Set environment variables or use .env file:
       - TELEGRAM_API_ID
       - TELEGRAM_API_HASH
    3. Run the script with desired commands

Examples:
    python fetch_messages.py --list-chats
    python fetch_messages.py --chat "Chat Name" --limit 100
    python fetch_messages.py --chat-id 123456789 --output messages.json
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

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
except ImportError:
    print("Error: Telethon library not found.")
    print("Install it with: pip install telethon")
    sys.exit(1)


# Default paths
SESSION_DIR = Path(__file__).parent / "sessions"
OUTPUT_DIR = Path(__file__).parent / "exports"


def get_credentials() -> tuple[str, str]:
    """Get Telegram API credentials from environment variables."""
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        # Try loading from .env file
        env_file = Path(__file__).parent / ".env"
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
        print("Error: Telegram API credentials not found.")
        print()
        print("Please set the following environment variables:")
        print("  TELEGRAM_API_ID=your_api_id")
        print("  TELEGRAM_API_HASH=your_api_hash")
        print()
        print("Or create a .env file in the telegram directory with:")
        print("  TELEGRAM_API_ID=your_api_id")
        print("  TELEGRAM_API_HASH=your_api_hash")
        print()
        print("Get your API credentials from: https://my.telegram.org")
        sys.exit(1)

    return api_id, api_hash


def serialize_message(message: Message) -> dict:
    """Convert a Telegram message to a JSON-serializable dictionary."""
    data = {
        "id": message.id,
        "date": message.date.isoformat() if message.date else None,
        "text": message.text or message.message or "",
        "out": message.out,  # True if sent by the user
        "reply_to_msg_id": message.reply_to.reply_to_msg_id if message.reply_to else None,
        "edit_date": message.edit_date.isoformat() if message.edit_date else None,
        "forwards": message.forwards,
        "views": message.views,
    }

    # Handle sender info
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

    # Handle media
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


async def list_chats(client: TelegramClient, limit: int = 100) -> list[dict]:
    """List all available chats/dialogs."""
    dialogs = await client.get_dialogs(limit=limit)
    return [serialize_chat(d) for d in dialogs]


async def fetch_messages(
    client: TelegramClient,
    chat_identifier: str | int,
    limit: Optional[int] = None,
    offset_date: Optional[datetime] = None,
    min_id: int = 0,
    max_id: int = 0,
) -> tuple[dict, list[dict]]:
    """
    Fetch messages from a specific chat.

    Args:
        client: The Telegram client
        chat_identifier: Chat name, username, or ID
        limit: Maximum number of messages to fetch (None for all)
        offset_date: Fetch messages before this date
        min_id: Minimum message ID to fetch
        max_id: Maximum message ID to fetch

    Returns:
        Tuple of (chat_info, messages)
    """
    # Get the entity
    try:
        if isinstance(chat_identifier, int):
            entity = await client.get_entity(chat_identifier)
        else:
            entity = await client.get_entity(chat_identifier)
    except ValueError as e:
        print(f"Error: Could not find chat '{chat_identifier}'")
        print("Use --list-chats to see available chats")
        raise

    # Get chat info
    chat_info = {
        "id": entity.id,
        "type": type(entity).__name__.lower(),
        "name": getattr(entity, "title", None)
        or getattr(entity, "first_name", None)
        or str(entity.id),
        "username": getattr(entity, "username", None),
    }

    # Fetch messages
    messages = []
    async for message in client.iter_messages(
        entity,
        limit=limit,
        offset_date=offset_date,
        min_id=min_id,
        max_id=max_id,
    ):
        if isinstance(message, Message):
            messages.append(serialize_message(message))

    return chat_info, messages


async def main():
    parser = argparse.ArgumentParser(
        description="Fetch messages from Telegram chats and channels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-chats
  %(prog)s --chat "My Channel" --limit 100
  %(prog)s --chat-id 123456789 --output backup.json
  %(prog)s --chat "@username" --after "2024-01-01"
        """,
    )

    # Action arguments
    parser.add_argument(
        "--list-chats",
        action="store_true",
        help="List all available chats and channels",
    )
    parser.add_argument(
        "--chat",
        type=str,
        help="Chat name or @username to fetch messages from",
    )
    parser.add_argument(
        "--chat-id",
        type=int,
        help="Chat ID to fetch messages from",
    )

    # Filtering options
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of messages to fetch (default: all)",
    )
    parser.add_argument(
        "--after",
        type=str,
        help="Fetch messages after this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--before",
        type=str,
        help="Fetch messages before this date (YYYY-MM-DD)",
    )

    # Output options
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (default: exports/<chat_name>_<timestamp>.json)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    # Session options
    parser.add_argument(
        "--session",
        type=str,
        default="telegram_archival",
        help="Session name for authentication persistence",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.list_chats and not args.chat and not args.chat_id:
        parser.print_help()
        print("\nError: Please specify --list-chats, --chat, or --chat-id")
        sys.exit(1)

    # Get credentials
    api_id, api_hash = get_credentials()

    # Create session directory
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_path = SESSION_DIR / args.session

    # Create client
    client = TelegramClient(str(session_path), api_id, api_hash)

    try:
        await client.start()
        print("Successfully connected to Telegram!")

        if args.list_chats:
            # List all chats
            print("\nFetching chats...")
            chats = await list_chats(client)

            print(f"\nFound {len(chats)} chats:\n")
            print(f"{'ID':<15} {'Type':<12} {'Name':<40} {'Username':<20}")
            print("-" * 90)

            for chat in chats:
                username = f"@{chat['username']}" if chat["username"] else ""
                name = chat["name"][:38] if chat["name"] else ""
                print(f"{chat['id']:<15} {chat['type']:<12} {name:<40} {username:<20}")

        else:
            # Fetch messages from specified chat
            chat_identifier = args.chat_id if args.chat_id else args.chat

            # Parse date filters
            offset_date = None
            if args.before:
                offset_date = datetime.strptime(args.before, "%Y-%m-%d")

            min_id = 0
            # Note: 'after' date filtering is done post-fetch since Telethon
            # doesn't support min_date directly

            print(f"\nFetching messages from: {chat_identifier}")
            if args.limit:
                print(f"Limit: {args.limit} messages")

            chat_info, messages = await fetch_messages(
                client,
                chat_identifier,
                limit=args.limit,
                offset_date=offset_date,
            )

            # Filter by 'after' date if specified
            if args.after:
                after_date = datetime.fromisoformat(args.after)
                messages = [
                    m for m in messages
                    if m["date"] and datetime.fromisoformat(m["date"]) >= after_date
                ]

            print(f"Fetched {len(messages)} messages")

            # Prepare output
            output_data = {
                "export_date": datetime.now().isoformat(),
                "chat": chat_info,
                "message_count": len(messages),
                "messages": messages,
            }

            # Determine output path
            if args.output:
                output_path = Path(args.output)
            else:
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                safe_name = "".join(
                    c if c.isalnum() or c in "-_" else "_"
                    for c in chat_info["name"]
                )
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = OUTPUT_DIR / f"{safe_name}_{timestamp}.json"

            # Write output
            with open(output_path, "w", encoding="utf-8") as f:
                if args.pretty:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(output_data, f, ensure_ascii=False)

            print(f"Messages saved to: {output_path}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
