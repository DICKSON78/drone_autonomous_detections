# PC4 Feedback Service API Documentation

## Base URL
```
http://localhost:8005
http://PC4_IP:8005
```

## Overview
The PC4 Feedback Service provides a REST API for Text-to-Speech (TTS) functionality, voice feedback, and audio management for the drone system.

## Authentication
Currently, the API does not require authentication. For production use, consider adding API keys or OAuth.

## Endpoints

### Health Check

#### GET /health
Check if the service is healthy and running.

**Response:**
```json
{
  "status": "healthy",
  "service": "feedback-service",
  "audio_ok": true,
  "queue_size": 0,
  "timestamp": 1234567890.0
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is unhealthy

**Example:**
```bash
curl http://localhost:8005/health
```

---

### Speak

#### POST /speak
Convert text to speech and play it through the audio device.

**Request Body:**
```json
{
  "message": "Hello, this is a test message",
  "priority": "normal"
}
```

**Parameters:**
- `message` (string, required): The text to speak. Maximum 500 characters.
- `priority` (string, optional): Message priority. Values: `low`, `normal`, `high`, `emergency`. Default: `normal`.

**Response:**
```json
{
  "status": "ok",
  "message": "Hello, this is a test message",
  "priority": "normal",
  "spoken": true,
  "queue_position": 0,
  "timestamp": 1234567890.0
}
```

**Status Codes:**
- `200 OK` - Message queued for speech
- `400 Bad Request` - Invalid request parameters
- `500 Internal Server Error` - TTS engine error

**Example:**
```bash
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, drone system", "priority": "normal"}'
```

---

### Announce

#### POST /announce
Announce a predefined event with a pre-configured message.

**Request Body:**
```json
{
  "event": "takeoff",
  "details": "Ready for flight"
}
```

**Parameters:**
- `event` (string, required): Event type. Values: `startup`, `shutdown`, `low_battery`, `obstacle`, `landing`, `takeoff`, `mission_done`, `emergency`.
- `details` (string, optional): Additional details to append to the message.

**Response:**
```json
{
  "status": "announced",
  "event": "takeoff",
  "message": "Drone is taking off. Ready for flight",
  "priority": "normal",
  "spoken": true,
  "timestamp": 1234567890.0
}
```

**Status Codes:**
- `200 OK` - Event announced
- `400 Bad Request` - Invalid event type
- `500 Internal Server Error` - TTS engine error

**Example:**
```bash
curl -X POST http://localhost:8005/announce \
  -H "Content-Type: application/json" \
  -d '{"event": "takeoff", "details": "Ready for flight"}'
```

**Available Events:**
| Event | Default Message | Priority |
|-------|-----------------|----------|
| startup | "Drone system starting up" | normal |
| shutdown | "Drone system shutting down" | normal |
| low_battery | "Battery level is low" | high |
| obstacle | "Obstacle detected ahead" | high |
| landing | "Drone is landing" | normal |
| takeoff | "Drone is taking off" | normal |
| mission_done | "Mission complete" | normal |
| emergency | "Emergency situation detected" | emergency |

---

### List Voices

#### GET /voices
Get list of available TTS voices.

**Response:**
```json
{
  "voices": [
    {
      "id": 0,
      "name": "English (US) - Male",
      "language": "en-US",
      "gender": "male"
    },
    {
      "id": 1,
      "name": "English (US) - Female",
      "language": "en-US",
      "gender": "female"
    }
  ],
  "current_voice": 0,
  "count": 2
}
```

**Status Codes:**
- `200 OK` - Voices listed successfully

**Example:**
```bash
curl http://localhost:8005/voices
```

---

### List Audio Devices

#### GET /audio-devices
Get list of available audio output devices.

**Response:**
```json
{
  "devices": [
    {
      "id": "default",
      "name": "Default Audio Device",
      "type": "output",
      "available": true
    },
    {
      "id": "pulse",
      "name": "PulseAudio",
      "type": "output",
      "available": true
    }
  ],
  "current_device": "default",
  "count": 2
}
```

**Status Codes:**
- `200 OK` - Devices listed successfully

**Example:**
```bash
curl http://localhost:8005/audio-devices
```

---

### Service Statistics

#### GET /stats
Get service statistics and performance metrics.

**Response:**
```json
{
  "service": "feedback-service",
  "version": "1.0.0",
  "uptime": 3600.5,
  "queue_stats": {
    "size": 0,
    "max_size": 100,
    "processed": 150,
    "failed": 2
  },
  "audio_stats": {
    "audio_ok": true,
    "current_device": "default",
    "volume": 0.8,
    "rate": 150
  },
  "kafka_stats": {
    "connected": true,
    "topics_subscribed": 3,
    "messages_consumed": 500,
    "messages_published": 150
  },
  "timestamp": 1234567890.0
}
```

**Status Codes:**
- `200 OK` - Statistics retrieved successfully

**Example:**
```bash
curl http://localhost:8005/stats
```

---

### Set Voice

#### POST /voice
Set the active TTS voice.

**Request Body:**
```json
{
  "voice_index": 1
}
```

**Parameters:**
- `voice_index` (integer, required): Index of the voice to use.

**Response:**
```json
{
  "status": "ok",
  "previous_voice": 0,
  "current_voice": 1,
  "voice_name": "English (US) - Female",
  "timestamp": 1234567890.0
}
```

**Status Codes:**
- `200 OK` - Voice changed successfully
- `400 Bad Request` - Invalid voice index
- `500 Internal Server Error` - Voice change failed

**Example:**
```bash
curl -X POST http://localhost:8005/voice \
  -H "Content-Type: application/json" \
  -d '{"voice_index": 1}'
```

---

### Set Volume

#### POST /volume
Set the audio volume level.

**Request Body:**
```json
{
  "volume": 0.9
}
```

**Parameters:**
- `volume` (float, required): Volume level between 0.0 and 1.0.

**Response:**
```json
{
  "status": "ok",
  "previous_volume": 0.8,
  "current_volume": 0.9,
  "timestamp": 1234567890.0
}
```

**Status Codes:**
- `200 OK` - Volume changed successfully
- `400 Bad Request` - Invalid volume value
- `500 Internal Server Error` - Volume change failed

**Example:**
```bash
curl -X POST http://localhost:8005/volume \
  -H "Content-Type: application/json" \
  -d '{"volume": 0.9}'
```

---

### Set Speech Rate

#### POST /rate
Set the speech rate (words per minute).

**Request Body:**
```json
{
  "rate": 120
}
```

**Parameters:**
- `rate` (integer, required): Speech rate in words per minute. Range: 50-300.

**Response:**
```json
{
  "status": "ok",
  "previous_rate": 150,
  "current_rate": 120,
  "timestamp": 1234567890.0
}
```

**Status Codes:**
- `200 OK` - Rate changed successfully
- `400 Bad Request` - Invalid rate value
- `500 Internal Server Error` - Rate change failed

**Example:**
```bash
curl -X POST http://localhost:8005/rate \
  -H "Content-Type: application/json" \
  -d '{"rate": 120}'
```

---

### Clear Queue

#### POST /queue/clear
Clear all pending messages from the speech queue.

**Response:**
```json
{
  "status": "ok",
  "messages_cleared": 5,
  "queue_size": 0,
  "timestamp": 1234567890.0
}
```

**Status Codes:**
- `200 OK` - Queue cleared successfully

**Example:**
```bash
curl -X POST http://localhost:8005/queue/clear
```

---

### Get Queue Status

#### GET /queue
Get current queue status.

**Response:**
```json
{
  "queue_size": 3,
  "max_size": 100,
  "messages": [
    {
      "message": "First message",
      "priority": "high",
      "position": 0
    },
    {
      "message": "Second message",
      "priority": "normal",
      "position": 1
    },
    {
      "message": "Third message",
      "priority": "low",
      "position": 2
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Queue status retrieved successfully

**Example:**
```bash
curl http://localhost:8005/queue
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error message",
  "status_code": 400,
  "timestamp": 1234567890.0
}
```

### Common Error Codes:
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Endpoint not found
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service unhealthy

---

## Rate Limiting

Currently, the API does not have rate limiting. For production use, consider implementing rate limiting to prevent abuse:

- Suggested limit: 60 requests per minute per IP
- Emergency messages should bypass rate limiting

---

## Priority Levels

Messages are processed based on priority:

1. **emergency** - Highest priority, processed first, can interrupt current speech
2. **high** - High priority, processed before normal messages
3. **normal** - Standard priority, default
4. **low** - Lowest priority, processed last

---

## Message Queue

The service uses a priority queue for message processing:

- Maximum queue size: 100 messages (configurable)
- Messages are processed in priority order
- Emergency messages can interrupt current speech
- Queue status available via `/queue` endpoint

---

## Kafka Integration

The service integrates with Kafka for message consumption and publishing:

**Input Topics:**
- `drone.commands.feedback` - Command feedback messages
- `drone.detections.objects` - Object detection alerts
- `drone.navigation.result` - Navigation results

**Output Topics:**
- `drone.feedback.spoken` - Messages that have been spoken
- `drone.feedback.status` - Service status updates

---

## Configuration

The service can be configured via:

1. **Environment Variables** (docker-compose.yml):
   - `KAFKA_BOOTSTRAP_SERVERS` - Kafka broker addresses
   - `TTS_RATE` - Default speech rate
   - `TTS_VOLUME` - Default volume
   - `TTS_VOICE_INDEX` - Default voice index
   - `PORT` - Service port

2. **Configuration Files** (config/ directory):
   - `tts_config.yaml` - TTS and audio settings
   - `feedback_config.yaml` - Service configuration
   - `kafka_topics.yaml` - Kafka topic configuration

---

## Testing the API

### Using curl

```bash
# Health check
curl http://localhost:8005/health

# Speak a message
curl -X POST http://localhost:8005/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Test message", "priority": "normal"}'

# Announce an event
curl -X POST http://localhost:8005/announce \
  -H "Content-Type: application/json" \
  -d '{"event": "takeoff"}'

# Get statistics
curl http://localhost:8005/stats

# List voices
curl http://localhost:8005/voices
```

### Using Python

```python
import requests

BASE_URL = "http://localhost:8005"

# Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# Speak a message
response = requests.post(
    f"{BASE_URL}/speak",
    json={"message": "Test message", "priority": "normal"}
)
print(response.json())

# Announce an event
response = requests.post(
    f"{BASE_URL}/announce",
    json={"event": "takeoff", "details": "Ready for flight"}
)
print(response.json())

# Get statistics
response = requests.get(f"{BASE_URL}/stats")
print(response.json())
```

### Using JavaScript

```javascript
const BASE_URL = "http://localhost:8005";

// Health check
fetch(`${BASE_URL}/health`)
  .then(res => res.json())
  .then(data => console.log(data));

// Speak a message
fetch(`${BASE_URL}/speak`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: "Test message",
    priority: "normal"
  })
})
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## WebSocket Support

Currently, the Feedback Service does not support WebSocket connections. All communication is via REST API.

---

## Versioning

The API follows semantic versioning. Current version: `1.0.0`

---

## Changelog

### Version 1.0.0
- Initial release
- Basic TTS functionality
- REST API endpoints
- Kafka integration
- Priority queue system
