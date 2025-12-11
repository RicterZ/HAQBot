HAQBot
================
QQ Bot for controlling Home Assistant devices via natural language conversation

## Features

Receives messages from QQ group chats and connects to Home Assistant's conversation agent (Ollama) to control devices and services.

## How It Works

```
QQ Message → NapCat WebSocket → QQ Bot → HA Conversation API → Ollama Agent → Device Control
                ↓                                                      ↓
            Response ← QQ Reply ← HA Response ← Execution Result
```

1. Connect to NapCat (QQ bot framework) via WebSocket
2. Receive messages from QQ group chats
3. Forward messages to Home Assistant's Conversation API
4. HA's Ollama conversation agent processes and executes device control
5. Return execution results to QQ users

## Configuration

### Environment Variables

Create a `.env` file (refer to `.env.example`):

```env
# NapCat WebSocket connection URL
NAPCAT_API=ws://napcat:3001

# Home Assistant configuration
HA_URL=http://homeassistant:8123
HA_TOKEN=your_long_lived_access_token_here
HA_AGENT_ID=conversant.ollama_conversation

# QQ account (optional)
ACCOUNT=2167634556
```

### Getting HA Token

1. Log in to Home Assistant
2. Click Profile → Long-Lived Access Tokens
3. Create a new token and copy it

### Configuring Conversation Agent

Ensure that the `conversant.ollama_conversation` conversation agent is configured in Home Assistant.

## Usage

1. Send a message in a QQ group (no command prefix required)
2. The bot will forward the message to HA's conversation agent
3. The conversation agent processes and executes the corresponding device control
4. Returns the execution result

### Example

- User: "Turn on the living room light"
- Bot: "The living room light has been turned on"

## Development

### Install Dependencies

```bash
poetry install
```

### Run

```bash
poetry run python src/meteion/main.py
```

### Docker Run

```bash
docker-compose up -d
```
