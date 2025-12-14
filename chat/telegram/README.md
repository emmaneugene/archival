# Telegram Message Fetcher

A Python utility to fetch and archive messages from your personal Telegram channels and chats.

## Setup

### 1. Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Go to "API development tools"
4. Create a new application (or use existing)
5. Copy your `api_id` and `api_hash`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Credentials

Create a `.env` file in this directory:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
```

Alternatively, set environment variables:

```bash
export TELEGRAM_API_ID=your_api_id
export TELEGRAM_API_HASH=your_api_hash
```

## Usage

### First Run - Authentication

On first run, you'll be prompted to enter your phone number and the verification code sent to your Telegram app. This creates a session file so you won't need to authenticate again.

### List Available Chats

```bash
python fetch_messages.py --list-chats
```

### Fetch Messages from a Chat

By chat name:
```bash
python fetch_messages.py --chat "Chat Name"
```

By username:
```bash
python fetch_messages.py --chat "@username"
```

By chat ID:
```bash
python fetch_messages.py --chat-id 123456789
```

### Options

| Option | Description |
|--------|-------------|
| `--list-chats` | List all available chats and channels |
| `--chat NAME` | Chat name or @username to fetch from |
| `--chat-id ID` | Chat ID to fetch from |
| `--limit N` | Maximum number of messages (default: all) |
| `--after DATE` | Fetch messages after date (YYYY-MM-DD) |
| `--before DATE` | Fetch messages before date (YYYY-MM-DD) |
| `--output FILE` | Output file path |
| `--pretty` | Pretty-print JSON output |
| `--session NAME` | Session name for auth persistence |

### Examples

Fetch last 100 messages:
```bash
python fetch_messages.py --chat "My Channel" --limit 100
```

Fetch messages from 2024:
```bash
python fetch_messages.py --chat "My Channel" --after "2024-01-01" --before "2025-01-01"
```

Export with pretty formatting:
```bash
python fetch_messages.py --chat "@channel" --output backup.json --pretty
```

## Output Format

Messages are exported to JSON with the following structure:

```json
{
  "export_date": "2024-12-14T10:30:00",
  "chat": {
    "id": 123456789,
    "type": "channel",
    "name": "My Channel",
    "username": "mychannel"
  },
  "message_count": 150,
  "messages": [
    {
      "id": 123,
      "date": "2024-12-01T12:00:00",
      "text": "Hello world!",
      "out": false,
      "reply_to_msg_id": null,
      "edit_date": null,
      "forwards": 5,
      "views": 100,
      "sender": {
        "type": "user",
        "id": 987654321,
        "first_name": "John",
        "last_name": "Doe",
        "username": "johndoe"
      },
      "media": null
    }
  ]
}
```

## File Structure

```
telegram/
├── fetch_messages.py    # Main script
├── requirements.txt     # Python dependencies
├── .env                 # Your credentials (not tracked)
├── .env.example         # Example credentials file
├── .gitignore           # Git ignore rules
├── sessions/            # Auth session files (not tracked)
└── exports/             # Exported messages (not tracked)
```

## Security Notes

- Never share your `.env` file or session files
- Session files contain your authentication - treat them like passwords
- The `.gitignore` is configured to exclude sensitive files
