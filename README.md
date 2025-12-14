# HAQBot

[English](README.md) | [中文](README_CN.md)

QQ Bot for controlling Home Assistant devices via natural language conversation.

## Features

- **Natural Language Control**: Control Home Assistant devices through text or voice messages in QQ groups
- **Direct Command Control**: Fast device control via commands (`/turnon`, `/turnoff`, `/toggle`) without LLM processing
- **Webhook Notifications**: Home Assistant can send proactive notifications to QQ groups via webhook API
- **Voice Recognition**: Automatically transcribes voice messages using Tencent Cloud ASR API (optional)
- **Multimodal Support**: Send text messages with files or video streams through webhook
- **Entity Caching**: In-memory cache for fast entity lookup without repeated API calls
- **Permission Control**: Restrict device control to specific QQ users via environment variable
- **Internationalization**: Support for Chinese and English languages

## Quick Start

### Prerequisites

- Home Assistant with Conversation Agent (Ollama) configured
- NapCat QQ bot framework
- (Optional) Tencent Cloud ASR credentials for voice recognition

### Installation

1. Clone this repository
2. Copy `.env.default` to `.env` and configure your settings
3. Run with Docker Compose:

```bash
docker-compose up -d
```

Or run directly:

```bash
poetry install
poetry run python src/maid/main.py
```

## Configuration

### Environment Variables

Create a `.env` file (refer to `.env.default`):

```env
# NapCat WebSocket connection URL
NAPCAT_API=ws://napcat:3001

# Home Assistant configuration
HA_URL=http://homeassistant:8123
HA_TOKEN=your_long_lived_access_token_here
HA_AGENT_ID=conversant.ollama_conversation

# QQ account (required) - Bot's QQ number
ACCOUNT=your_qq_account_number

# Display nickname (optional, default: メイド)
DISPLAY_NICKNAME=メイド

# Permission control (optional)
# Comma or space separated QQ numbers allowed to control devices
# If empty, all users can control devices
ALLOWED_SENDERS=123456789 987654321

# Language setting (optional, default: zh_CN)
LANGUAGE=zh_CN

# Debug mode (optional, default: false)
DEBUG=false

# Webhook configuration (optional)
WEBHOOK_PORT=8080
WEBHOOK_TOKEN=your_webhook_token_here

# Tencent Cloud ASR (optional, for voice recognition)
TENCENT_SECRET_ID=your_tencent_secret_id
TENCENT_SECRET_KEY=your_tencent_secret_key
TENCENT_ASR_ENGINE=16k_zh
TENCENT_ASR_REGION=
```

### Configuration Guide

#### Home Assistant Token

1. Log in to Home Assistant
2. Go to Profile → Long-Lived Access Tokens
3. Create a new token and copy it to `HA_TOKEN`

#### Conversation Agent

Ensure that the `conversant.ollama_conversation` conversation agent is configured in Home Assistant.

---

## Module 1: Command Interface

The bot supports two ways to control Home Assistant devices: **direct commands** and **natural language messages**.

### Natural Language Messages

Simply send a message in a QQ group (no command prefix or @ required). The bot will:
1. Forward the message to Home Assistant's conversation agent
2. Process and execute device control commands
3. Return the execution result

**Examples:**
- User: "Turn on the living room light"
- Bot: "The living room light has been turned on"

**Voice Messages:**
- Send a voice message in the group
- Bot automatically transcribes and processes it (requires voice recognition module configured)
- Returns the response

> **Note**: If voice recognition fails, the bot will silently skip the message to avoid spam.

### Direct Commands

The bot supports direct commands for faster device control without LLM processing:

#### Device Control Commands

- `/turnon <entity_id> [<entity_id2> ...]` - Turn on device(s)
  - Supports entity ID (e.g., `light.living_room`), friendly name, or alias
  - Can control multiple devices at once
  - Example: `/turnon 客厅灯` or `/turnon light.living_room light.bedroom`
  - Supports quoted names with spaces: `/turnon "Apple TV"`

- `/turnoff <entity_id> [<entity_id2> ...]` - Turn off device(s)
  - Same as `/turnon` but turns devices off

- `/toggle <entity_id> [<entity_id2> ...]` - Toggle device state(s)
  - Toggles the state of specified device(s)

#### Information Commands

- `/info` - Get Home Assistant context information
  - Shows active lights, climate devices, temperature, humidity, and important statuses

- `/light` - List all light devices
  - Groups devices by area
  - Shows device name and state summary

- `/switch` - List all switch devices
  - Same as `/light` but for switches

- `/search <query>` - Fuzzy search entities
  - Search entities by entity ID, friendly name, or alias (case-insensitive partial match)
  - Returns matching entities with their entity ID and friendly name
  - Example: `/search 灯` or `/search light`

- `/help` - Show all supported commands and descriptions

#### Command Features

- **Entity Lookup**: Commands support three ways to identify devices:
  1. Entity ID: `light.living_room`
  2. Friendly Name: `客厅灯`
  3. Alias: Any alias configured in Home Assistant

- **Multiple Devices**: Control multiple devices in one command by separating them with spaces

- **Quoted Names**: Use quotes for entity names with spaces: `/turnon "Living Room Light"`

- **Permission Control**: If `ALLOWED_SENDERS` is set, only specified QQ users can use control commands (`/turnon`, `/turnoff`, `/toggle`). Information commands (`/info`, `/light`, `/switch`, `/help`) are available to everyone.

- **Duplicate Alias Warning**: If multiple entities share the same alias, the bot will warn you but still control the first match

---

## Module 2: Webhook API

The bot provides webhook endpoints for Home Assistant to send proactive notifications to QQ groups. This allows you to customize messages and send multimodal content (text + video/files).

### Configuration

1. **Set Webhook Port** (optional, default: 8080):
   ```env
   WEBHOOK_PORT=8080
   ```

2. **Set Webhook Token** (optional, for security):
   ```env
   WEBHOOK_TOKEN=your_webhook_token_here
   ```

3. **Access Webhook**: The webhook server runs on `http://homeassistant-qq:8080` (or your configured port)

### Text Notification

Send simple text messages to QQ groups.

**Endpoint**: `POST http://homeassistant-qq:8080/webhook/notify`

**Request Body**:
```json
{
  "group_id": "123456789",
  "message": "Your notification message",
  "token": "optional_webhook_token"
}
```

**Parameters**:
- `group_id` (required): QQ group ID
- `message` (required): Message text
- `token` (optional): Authentication token (if `WEBHOOK_TOKEN` is set)

**Response**:
```json
{
  "status": "ok",
  "message": "Notification sent"
}
```

### Multimodal Notification

Send text messages with video streams or files. Supports HLS/m3u8 video streams (downloaded via ffmpeg).

**Endpoint**: `POST http://homeassistant-qq:8080/webhook/multimodal`

**Request Body**:
```json
{
  "group_id": "123456789",
  "message": "Optional text message",
  "url": "http://example.com/video_stream.m3u8",
  "token": "optional_webhook_token",
  "duration": 60
}
```

**Parameters**:
- `group_id` (required): QQ group ID
- `message` (optional): Message text
- `url` (optional): Video stream URL (supports HLS/m3u8, downloaded via ffmpeg)
- `token` (optional): Authentication token
- `duration` (optional): Video recording duration in seconds (default: 60)

> **Note**: At least one of `message` or `url` must be provided.

**Response**:
```json
{
  "status": "ok",
  "message": "Multimodal notification sent",
  "file_path": "/tmp/video_xxx.mp4"
}
```

### Home Assistant Integration

#### Configure REST Command

Add to your `configuration.yaml`:

```yaml
rest_command:
  homeassistant_qq:
    url: "http://homeassistant-qq:8080/webhook/notify"
    method: POST
    content_type: "application/json"
    payload: |
      {
        "group_id": "123456789",
        "message": "{{ message }}",
        "token": "{{ token | default('') }}"
      }
  
  homeassistant_qq_multimodal:
    url: "http://homeassistant-qq:8080/webhook/multimodal"
    method: POST
    content_type: "application/json"
    payload: |
      {
        "group_id": "123456789",
        "message": "{{ message }}",
        "url": "{{ url }}",
        "token": "{{ token | default('') }}",
        "duration": {{ duration | default(60) }}
      }
```

#### Automation Examples

**Simple Text Notification:**
```yaml
automation:
  - alias: "Washing Machine Finished"
    trigger:
      - platform: state
        entity_id: sensor.washing_machine_status
        to: "completed"
    action:
      - service: rest_command.homeassistant_qq
        data:
          message: "🧺 Washing machine finished!"
```

**Multimodal Notification with Video:**
```yaml
automation:
  - alias: "Door Motion Alert - Send QQ Notification"
    trigger:
      - trigger: state
        entity_id:
          - camera.front_door
        attribute: motion_video_time
        for:
          hours: 0
          minutes: 0
          seconds: 20
    action:
      - service: rest_command.homeassistant_qq_multimodal
        data:
          message: "⚠️ Motion detected at front door"
          url: "{{ state_attr('camera.front_door', 'stream_address') }}"
          duration: 30
```

**Custom Notification with Template:**
```yaml
automation:
  - alias: "Temperature Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.temperature
        above: 30
    action:
      - service: rest_command.homeassistant_qq
        data:
          message: >
            🌡️ Temperature Alert!
            Current: {{ states('sensor.temperature') }}°C
            Time: {{ now().strftime('%Y-%m-%d %H:%M') }}
```

### Security

If `WEBHOOK_TOKEN` is set, include it in the `token` field of webhook requests to prevent unauthorized access. The bot will return `401 Unauthorized` if the token doesn't match.

---

## Module 3: Voice Recognition (Optional)

The bot can automatically transcribe voice messages using Tencent Cloud ASR API. This module is **optional** - if not configured, the bot will only process text messages.

### Configuration

1. **Get Tencent Cloud Credentials**:
   - Log in to [Tencent Cloud Console](https://console.cloud.tencent.com/)
   - Navigate to **Access Management** → **API Key Management**
   - Create a new API key and copy `SecretId` and `SecretKey`

2. **Enable ASR Service**:
   - Enable the **Speech Recognition (ASR)** service in Tencent Cloud Console

3. **Configure Environment Variables**:
   ```env
   TENCENT_SECRET_ID=your_tencent_secret_id
   TENCENT_SECRET_KEY=your_tencent_secret_key
   TENCENT_ASR_ENGINE=16k_zh  # Optional, default: 16k_zh
   TENCENT_ASR_REGION=         # Optional, leave empty for default
   ```

### Supported Engines

- `16k_zh`: 16kHz Chinese recognition (default)
- `16k_en`: 16kHz English recognition
- `16k_zh_video`: 16kHz Chinese video recognition
- Other engines supported by Tencent Cloud ASR

### How It Works

1. User sends a voice message in QQ group
2. Bot downloads the audio file from NapCat
3. Bot converts audio to MP3 format
4. Bot sends audio to Tencent Cloud ASR API
5. Bot receives transcribed text
6. Bot processes text as natural language message

### Usage

Simply send a voice message in the QQ group. The bot will:
- Automatically transcribe the voice message
- Process the transcribed text as a natural language command
- Return the response

**Example:**
- User: [Sends voice message saying "打开客厅的灯"]
- Bot: "客厅的灯已打开"

### Error Handling

- If ASR credentials are not configured, voice messages are silently ignored
- If ASR fails, the bot will log a warning and skip the message to avoid spam
- Only MP3 format is supported (converted automatically from QQ voice format)

### Cost Considerations

Tencent Cloud ASR is a paid service. Check [Tencent Cloud Pricing](https://cloud.tencent.com/product/asr/pricing) for details. The bot uses sentence recognition API which charges per request.

---

## Deployment

### Docker Compose

```bash
docker-compose up -d
```

### Manual Deployment

```bash
# Install dependencies
poetry install

# Run the bot
poetry run python src/maid/main.py
```

The bot consists of two services:
- **WebSocket Client**: Connects to NapCat and handles QQ messages
- **Webhook Server**: FastAPI server for receiving webhook requests from Home Assistant

Both services run in the same process.

---

## Development

### Requirements

- Python 3.10+
- Poetry
- Docker & Docker Compose (for containerized deployment)

### Setup

```bash
# Install dependencies
poetry install

# Run locally
poetry run python src/maid/main.py

# Or use Docker
docker-compose up -d
```

### Project Structure

```
src/maid/
├── bot/              # WebSocket client for NapCat
├── clients/          # API clients (Home Assistant, Tencent ASR, NapCat)
├── handlers/         # Message handlers (conversation, commands)
├── models/           # Data models
├── services/         # Business logic (sender, etc.)
├── utils/            # Utilities (logger, i18n, entity cache)
└── webhook/          # Webhook API server
```

---

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

See the [LICENSE](LICENSE) file for details.

### Additional Terms

- **Commercial Use**: Commercial use is prohibited without explicit permission from the author
- **Attribution**: All redistributions and modifications must include original author attribution
