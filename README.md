# HAQBot

[English](README.md) | [中文](README_CN.md)

QQ Bot for controlling Home Assistant devices via natural language conversation.

## Features

- **Natural Language Control**: Control Home Assistant devices through text or voice messages in QQ groups
- **Direct Command Control**: Fast device control via commands (`/turnon`, `/turnoff`, `/toggle`) without LLM processing
- **Entity Lookup**: Support entity ID, friendly name, or alias for device control
- **Device Information**: Query device status and list devices by type (`/info`, `/light`, `/switch`)
- **Area Grouping**: Devices are grouped by area for better organization
- **Entity Caching**: In-memory cache for fast entity lookup without repeated API calls
- **Permission Control**: Restrict device control to specific QQ users via environment variable
- **Voice Recognition**: Automatically transcribes voice messages using Tencent Cloud ASR API
- **Conversation Context**: Maintains conversation context per group for natural dialogue
- **Webhook Notifications**: Home Assistant can send proactive notifications to QQ groups
- **Multimodal Support**: Send text messages with files or video streams
- **Asynchronous Processing**: Non-blocking message handling for better performance
- **Internationalization**: Support for Chinese and English languages

## Architecture

### Text Message Flow
```
QQ Message → NapCat WebSocket → Bot → HA Conversation API → Ollama Agent → Device Control → Response
```

### Voice Message Flow
```
QQ Voice → NapCat → Download Audio → Tencent ASR → Text → HA Conversation API → Response
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

# Tencent Cloud ASR (for voice recognition)
TENCENT_SECRET_ID=your_tencent_secret_id
TENCENT_SECRET_KEY=your_tencent_secret_key
TENCENT_ASR_ENGINE=16k_zh  # Optional, default: 16k_zh
TENCENT_ASR_REGION=         # Optional, leave empty for default

# QQ account (required) - Bot's QQ number
ACCOUNT=your_qq_account_number

# Permission control (optional)
# Comma or space separated QQ numbers allowed to control devices
# If empty, all users can control devices
ALLOWED_SENDERS=123456789 987654321

# Language setting (optional, default: zh_CN)
# Options: zh_CN (Chinese), en_US (English)
LANGUAGE=zh_CN

# Debug mode (optional, default: false)
# Set to true to enable debug logging
DEBUG=false

# Webhook configuration (optional)
WEBHOOK_PORT=8080
WEBHOOK_TOKEN=your_webhook_token_here
```

### Configuration Guide

#### Home Assistant Token

1. Log in to Home Assistant
2. Go to Profile → Long-Lived Access Tokens
3. Create a new token and copy it to `HA_TOKEN`

#### Conversation Agent

Ensure that the `conversant.ollama_conversation` conversation agent is configured in Home Assistant.

#### Tencent Cloud ASR (Optional)

1. Log in to [Tencent Cloud Console](https://console.cloud.tencent.com/)
2. Navigate to **Access Management** → **API Key Management**
3. Create a new API key and copy `SecretId` and `SecretKey`
4. Enable the **Speech Recognition (ASR)** service

> **Note**: Voice recognition is optional. Without ASR credentials, the bot will only process text messages.

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

## Usage

### Natural Language Control

Simply send a message in a QQ group (no command prefix or @ required). The bot will:
1. Forward the message to Home Assistant's conversation agent
2. Process and execute device control commands
3. Return the execution result

**Examples:**
- User: "Turn on the living room light"
- Bot: "The living room light has been turned on"

**Voice Message:**
- Send a voice message in the group
- Bot automatically transcribes and processes it
- Returns the response

> **Note**: If voice recognition fails, the bot will silently skip the message to avoid spam.

### Direct Commands

The bot supports direct commands for faster device control without LLM processing:

#### Device Control Commands

- `/turnon <entity_id> [<entity_id2> ...]` - Turn on device(s)
  - Supports entity ID (e.g., `light.living_room`), friendly name, or alias
  - Can control multiple devices at once
  - Example: `/turnon 客厅灯` or `/turnon light.living_room light.bedroom`

- `/turnoff <entity_id> [<entity_id2> ...]` - Turn off device(s)
  - Same as `/turnon` but turns devices off

- `/toggle <entity_id> [<entity_id2> ...]` - Toggle device state(s)
  - Toggles the state of specified device(s)

#### Information Commands

- `/info` - Get Home Assistant context information
  - Shows entity statistics by type (sensors, switches, lights, etc.)
  - Displays current states of important sensors

- `/light` - List all light devices
  - Groups devices by area
  - Shows friendly name, entity ID, and current state

- `/switch` - List all switch devices
  - Same as `/light` but for switches

- `/help` - Show all supported commands and descriptions

#### Command Features

- **Entity Lookup**: Commands support three ways to identify devices:
  1. Entity ID: `light.living_room`
  2. Friendly Name: `客厅灯`
  3. Alias: Any alias configured in Home Assistant

- **Multiple Devices**: Control multiple devices in one command by separating them with spaces

- **Permission Control**: If `ALLOWED_SENDERS` is set, only specified QQ users can use control commands (`/turnon`, `/turnoff`, `/toggle`). Information commands (`/info`, `/light`, `/switch`, `/help`) are available to everyone.

- **Duplicate Alias Warning**: If multiple entities share the same alias, the bot will warn you but still control the first match

## Webhook API

The bot provides webhook endpoints for Home Assistant to send proactive notifications to QQ groups.

### Text Notification

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

### Multimodal Notification

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
        "url": "{{ video_url }}",
        "token": "{{ token | default('') }}",
        "duration": {{ duration | default(60) }}
      }
```

#### Automation Examples

**Simple Notification:**
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

### Security

If `WEBHOOK_TOKEN` is set, include it in the `token` field of webhook requests to prevent unauthorized access.

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

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

See the [LICENSE](LICENSE) file for details.

### Additional Terms

- **Commercial Use**: Commercial use is prohibited without explicit permission from the author
- **Attribution**: All redistributions and modifications must include original author attribution
