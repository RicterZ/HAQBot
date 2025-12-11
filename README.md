HAQBot
================
QQ Bot for controlling Home Assistant devices via natural language conversation

## Features

- Receives messages from QQ group chats and connects to Home Assistant's conversation agent (Ollama) to control devices and services
- Webhook endpoint for Home Assistant to send proactive notifications to QQ groups

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

# Webhook configuration (optional)
WEBHOOK_PORT=8080
WEBHOOK_TOKEN=your_webhook_token_here
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

## Webhook Notifications

The bot provides a webhook endpoint that allows Home Assistant to send proactive notifications to QQ groups when certain events occur (e.g., washing machine finished, air conditioner turned on).

### Webhook Endpoint

- **URL**: `http://homeassistant-qq:8080/webhook/notify`
- **Method**: `POST`
- **Content-Type**: `application/json`

### Request Body

```json
{
  "group_id": "123456789",
  "message": "Your notification message",
  "token": "optional_webhook_token"
}
```

### Parameters

- `group_id` (required): QQ group ID to send the message to
- `message` (required): Message text to send
- `token` (optional): Webhook authentication token (if `WEBHOOK_TOKEN` is set)

### Home Assistant Automation Examples

#### Example 1: Washing Machine Finished Notification

```yaml
automation:
  - alias: "Washing Machine Finished Notification"
    trigger:
      - platform: state
        entity_id: sensor.washing_machine_status
        to: "completed"
    action:
      - service: http.post
        data:
          url: "http://homeassistant-qq:8080/webhook/notify"
          headers:
            Content-Type: application/json
          data:
            group_id: "123456789"
            message: "🧺 Washing machine finished! Clothes are ready to be taken out."
            token: "your_webhook_token_here"
```

#### Example 2: Air Conditioner Turned On Notification

```yaml
automation:
  - alias: "Air Conditioner Turned On Notification"
    trigger:
      - platform: state
        entity_id: climate.living_room_ac
        to: "cool"
    condition:
      - condition: state
        entity_id: climate.living_room_ac
        state: "cool"
    action:
      - service: http.post
        data:
          url: "http://homeassistant-qq:8080/webhook/notify"
          headers:
            Content-Type: application/json
          data:
            group_id: "123456789"
            message: "❄️ Air conditioner in living room has been turned on (Cooling mode)"
            token: "your_webhook_token_here"
```

#### Example 3: Door Opened Notification

```yaml
automation:
  - alias: "Front Door Opened Notification"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: "on"
    action:
      - service: http.post
        data:
          url: "http://homeassistant-qq:8080/webhook/notify"
          headers:
            Content-Type: application/json
          data:
            group_id: "123456789"
            message: "🚪 Front door has been opened"
            token: "your_webhook_token_here"
```

#### Example 4: Temperature Alert

```yaml
automation:
  - alias: "High Temperature Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.living_room_temperature
        above: 30
    action:
      - service: http.post
        data:
          url: "http://homeassistant-qq:8080/webhook/notify"
          headers:
            Content-Type: application/json
          data:
            group_id: "123456789"
            message: "🌡️ Temperature alert: Living room temperature is {{ states('sensor.living_room_temperature') }}°C"
            token: "your_webhook_token_here"
```

### Getting QQ Group ID

To get your QQ group ID, you can check the group information in NapCat or use the bot's logging output when it receives a message from the group.

### Security

If you set `WEBHOOK_TOKEN` in your environment variables, you must include the same token in the `token` field of your webhook requests. This prevents unauthorized access to the webhook endpoint.

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
